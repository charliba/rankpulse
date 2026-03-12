"""Management command to submit sitemaps to Google Search Console."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from apps.analytics.search_console import SearchConsoleClient
from apps.core.models import Site

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Submit sitemap(s) to Google Search Console for active sites."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--site-id", type=int, help="Specific site ID")
        parser.add_argument("--sitemap-url", type=str, help="Override sitemap URL")
        parser.add_argument("--list", action="store_true", help="List sitemaps instead of submitting")

    def handle(self, *args, **options) -> None:
        site_id = options.get("site_id")
        sitemap_override = options.get("sitemap_url")
        list_only = options.get("list", False)

        key_path = getattr(settings, "GSC_SERVICE_ACCOUNT_KEY_PATH", "")
        if not key_path:
            self.stdout.write(self.style.ERROR("GSC_SERVICE_ACCOUNT_KEY_PATH not configured."))
            return

        if site_id:
            sites = Site.objects.filter(pk=site_id, is_active=True)
        else:
            sites = Site.objects.filter(is_active=True, gsc_verified=True)

        if not sites.exists():
            self.stdout.write(self.style.WARNING("No sites found."))
            return

        for site in sites:
            site_url = site.gsc_site_url or site.url
            self.stdout.write(f"\n🗺️  Site: {site.name} ({site_url})")

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

            if list_only:
                result = client.list_sitemaps()
                if result["success"]:
                    for sm in result["sitemaps"]:
                        status = "⏳ pending" if sm["is_pending"] else "✅ OK"
                        self.stdout.write(f"  {status} {sm['path']}")
                    if not result["sitemaps"]:
                        self.stdout.write("  (no sitemaps registered)")
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ {result['error']}"))
            else:
                sitemap_url = sitemap_override or site.sitemap_url
                if not sitemap_url:
                    # Auto-construct from domain
                    sitemap_url = f"{site.url.rstrip('/')}/sitemap.xml"

                result = client.submit_sitemap(sitemap_url)
                if result["success"]:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Submitted: {sitemap_url}"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ {result['error']}"))

        self.stdout.write(self.style.SUCCESS("\nDone!"))
