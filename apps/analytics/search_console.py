"""Google Search Console API Client.

Fetches search performance data using the Search Console API v1.

Requirements:
    - Service account with Search Console access
    - google-api-python-client, google-auth installed

Reference: https://developers.google.com/webmaster-tools/v1/api_reference_index
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _get_service(service_account_key_path: str):
    """Build Search Console API service.

    Args:
        service_account_key_path: Path to the service account JSON key file.

    Returns:
        googleapiclient.discovery.Resource for searchconsole v1.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_file(
        service_account_key_path,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    return build("searchconsole", "v1", credentials=credentials)


class SearchConsoleClient:
    """Client for Google Search Console API.

    Usage:
        client = SearchConsoleClient(
            service_account_key_path="credentials/gsc.json",
            site_url="https://beezle.io",
        )
        data = client.fetch_performance(days=7)
    """

    def __init__(self, service_account_key_path: str, site_url: str) -> None:
        self.service_account_key_path = service_account_key_path
        self.site_url = site_url
        self._service = None

    @property
    def service(self):
        """Lazy-load the API service."""
        if self._service is None:
            self._service = _get_service(self.service_account_key_path)
        return self._service

    def fetch_performance(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int = 7,
        dimensions: list[str] | None = None,
        row_limit: int = 1000,
        dimension_filter_groups: list[dict] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch search performance data.

        Args:
            start_date: Start date. If None, uses `end_date - days`.
            end_date: End date. Defaults to 3 days ago (GSC data delay).
            days: Number of days to look back if start_date not set.
            dimensions: List of dimensions (date, query, page, device, country).
            row_limit: Max rows to return (max 25000).
            dimension_filter_groups: Optional filters.

        Returns:
            List of row dicts with 'keys' and metric values.
        """
        if end_date is None:
            end_date = date.today() - timedelta(days=3)  # GSC 3-day delay
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        if dimensions is None:
            dimensions = ["query", "page"]

        request_body: dict[str, Any] = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": dimensions,
            "rowLimit": min(row_limit, 25000),
            "dataState": "final",
        }
        if dimension_filter_groups:
            request_body["dimensionFilterGroups"] = dimension_filter_groups

        logger.info(
            "Fetching GSC data: %s → %s, dimensions=%s",
            start_date, end_date, dimensions,
        )

        try:
            response = (
                self.service.searchanalytics()
                .query(siteUrl=self.site_url, body=request_body)
                .execute()
            )
            rows = response.get("rows", [])
            logger.info("GSC returned %d rows", len(rows))
            return rows
        except Exception as exc:
            logger.error("GSC API error: %s", exc)
            return []

    def fetch_queries(
        self,
        days: int = 7,
        row_limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch top queries with clicks/impressions/ctr/position."""
        rows = self.fetch_performance(
            days=days,
            dimensions=["query"],
            row_limit=row_limit,
        )
        results = []
        for row in rows:
            results.append({
                "query": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1),
            })
        return results

    def fetch_pages(
        self,
        days: int = 7,
        row_limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch top pages with performance metrics."""
        rows = self.fetch_performance(
            days=days,
            dimensions=["page"],
            row_limit=row_limit,
        )
        results = []
        for row in rows:
            results.append({
                "page": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1),
            })
        return results

    def fetch_daily_totals(
        self,
        days: int = 28,
    ) -> list[dict[str, Any]]:
        """Fetch daily aggregated totals."""
        rows = self.fetch_performance(
            days=days,
            dimensions=["date"],
            row_limit=days,
        )
        results = []
        for row in rows:
            results.append({
                "date": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1),
            })
        return results

    def submit_url_for_indexing(self, url: str) -> dict[str, Any]:
        """Submit a URL for indexing via Indexing API.

        Note: Requires separate Indexing API credentials.
        """
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            self.service_account_key_path,
            scopes=["https://www.googleapis.com/auth/indexing"],
        )
        indexing_service = build("indexing", "v3", credentials=credentials)

        logger.info("Submitting URL for indexing: %s", url)
        try:
            response = (
                indexing_service.urlNotifications()
                .publish(body={"url": url, "type": "URL_UPDATED"})
                .execute()
            )
            logger.info("Indexing response: %s", response)
            return response
        except Exception as exc:
            logger.error("Indexing API error: %s", exc)
            return {"error": str(exc)}
