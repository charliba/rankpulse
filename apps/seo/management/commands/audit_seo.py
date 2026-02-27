"""Management command to run SEO audit on a site."""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandParser

from apps.core.models import Site
from apps.seo.auditor import SEOAuditor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run SEO audit on a site. Crawls pages, evaluates meta tags, content, and technical SEO."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("site_id", type=int, help="Site ID to audit")
        parser.add_argument("--max-pages", type=int, default=50, help="Max pages to crawl (default: 50)")

    def handle(self, *args, **options) -> None:
        site_id = options["site_id"]
        max_pages = options["max_pages"]

        try:
            site = Site.objects.get(pk=site_id, is_active=True)
        except Site.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Site #{site_id} não encontrado."))
            return

        self.stdout.write(f"🔍 Running SEO audit: {site.name} ({site.domain})")
        self.stdout.write(f"   Max pages: {max_pages}")

        auditor = SEOAuditor(site, max_pages=max_pages)
        audit = auditor.run()

        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"Score Geral: {audit.overall_score}/100")
        self.stdout.write(f"Páginas: {audit.pages_crawled}")
        self.stdout.write(f"Issues: {audit.issues_critical} critical, {audit.issues_warning} warning, {audit.issues_info} info")
        self.stdout.write(f"Status: {audit.status}")

        if audit.recommendations:
            self.stdout.write(f"\n📋 Recomendações:")
            for rec in audit.recommendations:
                self.stdout.write(f"  [{rec['priority']}] {rec['action']}")

        self.stdout.write(self.style.SUCCESS(f"\n✅ Audit #{audit.pk} concluído!"))
