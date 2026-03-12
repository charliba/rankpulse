"""Management command to fetch Google Search Console data."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from apps.analytics.models import SearchConsoleData
from apps.analytics.search_console import SearchConsoleClient
from apps.core.models import Site

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch Google Search Console data for all active sites (or a specific site)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--site-id", type=int, help="Specific site ID to fetch")
        parser.add_argument("--days", type=int, default=7, help="Number of days to fetch (default: 7)")

    def handle(self, *args, **options) -> None:
        site_id = options.get("site_id")
        days = options["days"]

        if site_id:
            sites = Site.objects.filter(pk=site_id, is_active=True)
        else:
            sites = Site.objects.filter(is_active=True, gsc_verified=True)

        if not sites.exists():
            self.stdout.write(self.style.WARNING("Nenhum site encontrado com GSC verificado."))
            return

        # Resolve service account key path
        key_path = getattr(settings, "GSC_SERVICE_ACCOUNT_KEY_PATH", "")
        if not key_path:
            self.stdout.write(self.style.ERROR(
                "GSC_SERVICE_ACCOUNT_KEY_PATH not set in settings/.env",
            ))
            return

        end_date = date.today() - timedelta(days=3)  # GSC data has ~3 day delay
        start_date = end_date - timedelta(days=days)

        for site in sites:
            self.stdout.write(f"\n📊 Fetching GSC: {site.name} ({start_date} → {end_date})")

            site_url = site.gsc_site_url or site.url
            try:
                if site.google_refresh_token:
                    client = SearchConsoleClient(
                        site_url=site_url,
                        refresh_token=site.google_refresh_token,
                    )
                else:
                    client = SearchConsoleClient(
                        service_account_key_path=key_path,
                        site_url=site_url,
                    )
                rows = client.fetch_performance(
                    start_date=start_date,
                    end_date=end_date,
                    dimensions=["query", "page"],
                    row_limit=1000,
                )

                rows_saved = 0
                for row in rows:
                    keys = row.get("keys", [])
                    query = keys[0] if len(keys) > 0 else ""
                    page = keys[1] if len(keys) > 1 else ""

                    SearchConsoleData.objects.update_or_create(
                        site=site,
                        date=end_date,
                        query=query,
                        page=page,
                        defaults={
                            "clicks": row.get("clicks", 0),
                            "impressions": row.get("impressions", 0),
                            "ctr": row.get("ctr", 0),
                            "position": row.get("position", 0),
                        },
                    )
                    rows_saved += 1

                self.stdout.write(self.style.SUCCESS(f"  ✅ {rows_saved} rows saved"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Error: {e}"))
                logger.exception("GSC fetch failed for %s", site.name)

        self.stdout.write(self.style.SUCCESS("\nDone!"))
