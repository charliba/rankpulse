"""GA4 Data API Client — Fetch reports from GA4.

Uses the Google Analytics Data API v1 to pull
traffic, engagement, and conversion data.

Reference: https://developers.google.com/analytics/devguides/reporting/data/v1
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _get_client(service_account_key_path: str):
    """Build GA4 Data API client."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_file(
        service_account_key_path,
    )
    return BetaAnalyticsDataClient(credentials=credentials)


class GA4ReportClient:
    """Client for GA4 Data API (reporting).

    Usage:
        client = GA4ReportClient(
            property_id="123456789",
            service_account_key_path="credentials/ga4.json",
        )
        data = client.get_organic_traffic(days=30)
    """

    def __init__(self, property_id: str, service_account_key_path: str) -> None:
        self.property_id = property_id
        self.service_account_key_path = service_account_key_path
        self._client = None

    @property
    def client(self):
        """Lazy-load the API client."""
        if self._client is None:
            self._client = _get_client(self.service_account_key_path)
        return self._client

    def _run_report(
        self,
        dimensions: list[str],
        metrics: list[str],
        start_date: str,
        end_date: str,
        dimension_filter: Any = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Execute a GA4 Data API report request."""
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )

        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit,
        )
        if dimension_filter:
            request.dimension_filter = dimension_filter

        try:
            response = self.client.run_report(request)
            results = []
            for row in response.rows:
                entry = {}
                for i, dim in enumerate(dimensions):
                    entry[dim] = row.dimension_values[i].value
                for i, met in enumerate(metrics):
                    entry[met] = row.metric_values[i].value
                results.append(entry)
            return results
        except Exception as exc:
            logger.error("GA4 Data API error: %s", exc)
            return []

    def get_organic_traffic(self, days: int = 30) -> list[dict]:
        """Get daily organic traffic sessions."""
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=days)).isoformat()

        from google.analytics.data_v1beta.types import (
            Filter,
            FilterExpression,
        )

        dim_filter = FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search"),
            )
        )

        return self._run_report(
            dimensions=["date"],
            metrics=["sessions", "totalUsers", "newUsers", "bounceRate"],
            start_date=start,
            end_date=end,
            dimension_filter=dim_filter,
        )

    def get_conversion_events(self, days: int = 30) -> list[dict]:
        """Get conversion event counts."""
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=days)).isoformat()

        return self._run_report(
            dimensions=["eventName"],
            metrics=["eventCount", "eventValue"],
            start_date=start,
            end_date=end,
        )

    def get_top_pages(self, days: int = 30, limit: int = 50) -> list[dict]:
        """Get top pages by sessions."""
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=days)).isoformat()

        return self._run_report(
            dimensions=["pagePath"],
            metrics=["sessions", "averageSessionDuration", "bounceRate"],
            start_date=start,
            end_date=end,
            limit=limit,
        )

    def get_traffic_sources(self, days: int = 30) -> list[dict]:
        """Get traffic source breakdown."""
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=days)).isoformat()

        return self._run_report(
            dimensions=["sessionDefaultChannelGroup"],
            metrics=["sessions", "totalUsers", "conversions"],
            start_date=start,
            end_date=end,
        )
