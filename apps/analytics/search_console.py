"""Google Search Console API Client.

Fetches search performance data, manages sitemaps, submits URLs for indexing,
and inspects URL index status using the Search Console + Indexing APIs.

Requirements:
    - Service account with Search Console access
    - google-api-python-client, google-auth installed

Reference:
    - https://developers.google.com/webmaster-tools/v1/api_reference_index
    - https://developers.google.com/search/apis/indexing-api/v3/reference
    - https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _get_service(service_account_key_path: str, readonly: bool = True):
    """Build Search Console API service.

    Args:
        service_account_key_path: Path to the service account JSON key file.
        readonly: If False, uses full webmasters scope (for sitemap submission).

    Returns:
        googleapiclient.discovery.Resource for searchconsole v1.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scope = (
        "https://www.googleapis.com/auth/webmasters.readonly"
        if readonly
        else "https://www.googleapis.com/auth/webmasters"
    )
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key_path,
        scopes=[scope],
    )
    return build("searchconsole", "v1", credentials=credentials)


def _get_indexing_service(service_account_key_path: str):
    """Build Indexing API v3 service.

    Args:
        service_account_key_path: Path to the service account JSON key file.

    Returns:
        googleapiclient.discovery.Resource for indexing v3.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_file(
        service_account_key_path,
        scopes=["https://www.googleapis.com/auth/indexing"],
    )
    return build("indexing", "v3", credentials=credentials)


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
        self._service_rw = None
        self._indexing_service = None

    @property
    def service(self):
        """Lazy-load the read-only API service."""
        if self._service is None:
            self._service = _get_service(self.service_account_key_path, readonly=True)
        return self._service

    @property
    def service_rw(self):
        """Lazy-load the read-write API service (for sitemap submission)."""
        if self._service_rw is None:
            self._service_rw = _get_service(self.service_account_key_path, readonly=False)
        return self._service_rw

    @property
    def indexing_service(self):
        """Lazy-load the Indexing API v3 service."""
        if self._indexing_service is None:
            self._indexing_service = _get_indexing_service(self.service_account_key_path)
        return self._indexing_service

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
        """Submit a URL for indexing via Indexing API v3.

        Args:
            url: Full URL to submit (e.g., https://beezle.io/blog/post-1/).

        Returns:
            Dict with Indexing API response or error.
        """
        logger.info("Submitting URL for indexing: %s", url)
        try:
            response = (
                self.indexing_service.urlNotifications()
                .publish(body={"url": url, "type": "URL_UPDATED"})
                .execute()
            )
            logger.info("Indexing response: %s", response)
            return {"success": True, "response": response}
        except Exception as exc:
            logger.error("Indexing API error: %s", exc)
            return {"success": False, "error": str(exc)}

    def remove_url_from_index(self, url: str) -> dict[str, Any]:
        """Request removal of a URL from the index.

        Args:
            url: Full URL to remove.

        Returns:
            Dict with Indexing API response or error.
        """
        logger.info("Requesting URL removal: %s", url)
        try:
            response = (
                self.indexing_service.urlNotifications()
                .publish(body={"url": url, "type": "URL_DELETED"})
                .execute()
            )
            logger.info("Removal response: %s", response)
            return {"success": True, "response": response}
        except Exception as exc:
            logger.error("Indexing API removal error: %s", exc)
            return {"success": False, "error": str(exc)}

    def batch_submit_urls(self, urls: list[str]) -> list[dict[str, Any]]:
        """Submit multiple URLs for indexing.

        Args:
            urls: List of full URLs to submit.

        Returns:
            List of results per URL.
        """
        results = []
        for url in urls:
            result = self.submit_url_for_indexing(url)
            result["url"] = url
            results.append(result)
        return results

    def get_indexing_status(self, url: str) -> dict[str, Any]:
        """Get the notification status for a URL.

        Args:
            url: URL to check.

        Returns:
            Dict with notification metadata or error.
        """
        try:
            response = (
                self.indexing_service.urlNotifications()
                .getMetadata(url=url)
                .execute()
            )
            return {"success": True, "metadata": response}
        except Exception as exc:
            logger.error("Indexing status error for %s: %s", url, exc)
            return {"success": False, "error": str(exc)}

    # ── Sitemap Management ──────────────────────────────────────

    def submit_sitemap(self, sitemap_url: str) -> dict[str, Any]:
        """Submit a sitemap to Google Search Console.

        Args:
            sitemap_url: Full URL to the sitemap
                         (e.g., https://beezle.io/sitemap.xml).

        Returns:
            Dict with success status.
        """
        logger.info("Submitting sitemap: %s for site %s", sitemap_url, self.site_url)
        try:
            self.service_rw.sitemaps().submit(
                siteUrl=self.site_url,
                feedpath=sitemap_url,
            ).execute()
            logger.info("Sitemap submitted successfully: %s", sitemap_url)
            return {"success": True, "sitemap_url": sitemap_url}
        except Exception as exc:
            logger.error("Sitemap submission error: %s", exc)
            return {"success": False, "error": str(exc)}

    def list_sitemaps(self) -> dict[str, Any]:
        """List all sitemaps registered for the site.

        Returns:
            Dict with list of sitemaps and their status.
        """
        logger.info("Listing sitemaps for %s", self.site_url)
        try:
            response = self.service_rw.sitemaps().list(
                siteUrl=self.site_url,
            ).execute()
            sitemaps = response.get("sitemap", [])
            results = []
            for sm in sitemaps:
                results.append({
                    "path": sm.get("path", ""),
                    "type": sm.get("type", ""),
                    "last_submitted": sm.get("lastSubmitted", ""),
                    "last_downloaded": sm.get("lastDownloaded", ""),
                    "is_pending": sm.get("isPending", False),
                    "warnings": sm.get("warnings", 0),
                    "errors": sm.get("errors", 0),
                    "contents": sm.get("contents", []),
                })
            logger.info("Found %d sitemaps", len(results))
            return {"success": True, "sitemaps": results, "count": len(results)}
        except Exception as exc:
            logger.error("Sitemap list error: %s", exc)
            return {"success": False, "error": str(exc)}

    def delete_sitemap(self, sitemap_url: str) -> dict[str, Any]:
        """Delete a sitemap from Google Search Console.

        Args:
            sitemap_url: Full URL of the sitemap to remove.

        Returns:
            Dict with success status.
        """
        logger.info("Deleting sitemap: %s for site %s", sitemap_url, self.site_url)
        try:
            self.service_rw.sitemaps().delete(
                siteUrl=self.site_url,
                feedpath=sitemap_url,
            ).execute()
            logger.info("Sitemap deleted: %s", sitemap_url)
            return {"success": True, "deleted": sitemap_url}
        except Exception as exc:
            logger.error("Sitemap delete error: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_sitemap(self, sitemap_url: str) -> dict[str, Any]:
        """Get details of a specific sitemap.

        Args:
            sitemap_url: Full URL of the sitemap.

        Returns:
            Dict with sitemap details or error.
        """
        try:
            response = self.service_rw.sitemaps().get(
                siteUrl=self.site_url,
                feedpath=sitemap_url,
            ).execute()
            return {"success": True, "sitemap": response}
        except Exception as exc:
            logger.error("Sitemap get error: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── URL Inspection ──────────────────────────────────────────

    def inspect_url(self, url: str) -> dict[str, Any]:
        """Inspect a URL's index status via the URL Inspection API.

        Args:
            url: Full URL to inspect (e.g., https://beezle.io/blog/post-1/).

        Returns:
            Dict with coverage state, indexing state, crawl info, etc.
        """
        logger.info("Inspecting URL: %s", url)
        try:
            response = self.service.urlInspection().index().inspect(
                body={
                    "inspectionUrl": url,
                    "siteUrl": self.site_url,
                },
            ).execute()

            result = response.get("inspectionResult", {})
            index_status = result.get("indexStatusResult", {})
            crawl_info = index_status.get("crawledAs", "")
            coverage = index_status.get("coverageState", "")
            verdict = index_status.get("verdict", "")
            indexing_state = index_status.get("indexingState", "")
            last_crawl = index_status.get("lastCrawlTime", "")
            page_fetch = index_status.get("pageFetchState", "")
            robots_state = index_status.get("robotsTxtState", "")
            referring_urls = index_status.get("referringUrls", [])

            mobile = result.get("mobileUsabilityResult", {})
            rich_results = result.get("richResultsResult", {})

            return {
                "success": True,
                "url": url,
                "verdict": verdict,
                "coverage_state": coverage,
                "indexing_state": indexing_state,
                "crawled_as": crawl_info,
                "last_crawl_time": last_crawl,
                "page_fetch_state": page_fetch,
                "robots_txt_state": robots_state,
                "referring_urls": referring_urls,
                "mobile_usability": mobile.get("verdict", ""),
                "rich_results": rich_results.get("verdict", ""),
            }
        except Exception as exc:
            logger.error("URL Inspection error for %s: %s", url, exc)
            return {"success": False, "url": url, "error": str(exc)}

    def batch_inspect_urls(self, urls: list[str]) -> list[dict[str, Any]]:
        """Inspect multiple URLs for index status.

        Args:
            urls: List of URLs to inspect.

        Returns:
            List of inspection results.
        """
        results = []
        for url in urls:
            result = self.inspect_url(url)
            results.append(result)
        return results

