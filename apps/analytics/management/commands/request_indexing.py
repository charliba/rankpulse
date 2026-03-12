"""Management command to request URL indexing via Google Indexing API."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from apps.analytics.search_console import SearchConsoleClient
from apps.core.models import Site

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Submit URLs for indexing via Google Indexing API."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--site-id", type=int, required=True, help="Site ID to index URLs for")
        parser.add_argument("--urls", nargs="+", help="Specific URLs to submit")
        parser.add_argument(
            "--blog", action="store_true",
            help="Auto-discover blog post URLs from the site",
        )
        parser.add_argument(
            "--inspect", action="store_true",
            help="Inspect URL index status instead of submitting",
        )
        parser.add_argument(
            "--all-pages", action="store_true",
            help="Submit key pages (home, vendas, plans, blog index)",
        )

    def handle(self, *args, **options) -> None:
        site_id = options["site_id"]
        urls = options.get("urls") or []
        blog_mode = options.get("blog", False)
        inspect_mode = options.get("inspect", False)
        all_pages = options.get("all_pages", False)

        key_path = getattr(settings, "GSC_SERVICE_ACCOUNT_KEY_PATH", "")
        if not key_path:
            self.stdout.write(self.style.ERROR("GSC_SERVICE_ACCOUNT_KEY_PATH not configured."))
            return

        try:
            site = Site.objects.get(pk=site_id, is_active=True)
        except Site.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Site {site_id} not found."))
            return

        site_url = site.gsc_site_url or site.url
        base_url = site.url.rstrip("/")

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

        # Build URL list
        if all_pages:
            urls.extend([
                f"{base_url}/",
                f"{base_url}/vendas/programa-de-indicacao/",
                f"{base_url}/vendas/embaixadores-de-marca/",
                f"{base_url}/vendas/como-funciona/",
                f"{base_url}/empresa/criar/",
                f"{base_url}/blog/",
                f"{base_url}/sitemap.xml",
            ])

        if blog_mode:
            # Try to fetch blog URLs from the sitemap or hardcode known paths
            self.stdout.write("📝 Fetching blog post URLs...")
            try:
                import httpx
                resp = httpx.get(f"{base_url}/sitemap.xml", timeout=15)
                if resp.status_code == 200:
                    import re
                    blog_urls = re.findall(r"<loc>(.*?/blog/.*?)</loc>", resp.text)
                    urls.extend(blog_urls)
                    self.stdout.write(f"  Found {len(blog_urls)} blog URLs in sitemap")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Could not fetch sitemap: {e}"))

        if not urls:
            self.stdout.write(self.style.WARNING("No URLs to process. Use --urls, --blog, or --all-pages."))
            return

        # Deduplicate
        urls = list(dict.fromkeys(urls))
        self.stdout.write(f"\n🔍 Processing {len(urls)} URLs for {site.name}")

        if inspect_mode:
            self.stdout.write("\n--- URL Inspection ---")
            for url in urls:
                result = client.inspect_url(url)
                if result.get("success"):
                    verdict = result.get("verdict", "UNKNOWN")
                    state = result.get("indexing_state", "")
                    emoji = "✅" if verdict == "PASS" else "⚠️" if verdict == "NEUTRAL" else "❌"
                    self.stdout.write(f"  {emoji} {url}")
                    self.stdout.write(f"      Verdict: {verdict} | Indexing: {state}")
                    if result.get("last_crawl_time"):
                        self.stdout.write(f"      Last crawl: {result['last_crawl_time']}")
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ {url}: {result.get('error', 'unknown')}"))
        else:
            self.stdout.write("\n--- Submitting for Indexing ---")
            results = client.batch_submit_urls(urls)
            success_count = 0
            for result in results:
                url = result.get("url", "")
                if result.get("success"):
                    self.stdout.write(self.style.SUCCESS(f"  ✅ {url}"))
                    success_count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ {url}: {result.get('error', '')}"))

            self.stdout.write(f"\nSubmitted: {success_count}/{len(urls)} URLs")

        self.stdout.write(self.style.SUCCESS("\nDone!"))
