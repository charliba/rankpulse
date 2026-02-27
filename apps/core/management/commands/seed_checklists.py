"""Management command to seed weekly checklist template."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.checklists.models import ChecklistTemplate, ChecklistTemplateItem


class Command(BaseCommand):
    help = "Seed the weekly SEO checklist template."

    def handle(self, *args, **options) -> None:
        template, created = ChecklistTemplate.objects.update_or_create(
            name="Checklist Semanal SEO",
            defaults={
                "description": "Checklist semanal de tráfego orgânico e SEO. "
                "Baseado nas melhores práticas de manutenção de sites.",
                "frequency": "weekly",
                "is_active": True,
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} template: {template}"))

        items = [
            # Analytics
            {"title": "Verificar GA4 — sessões, eventos, conversões", "category": "analytics", "tool_hint": "GA4", "order": 1},
            {"title": "Verificar novos sign-ups e origem do tráfego", "category": "analytics", "tool_hint": "GA4", "order": 2},
            {"title": "Revisar Key Events no GA4 (purchase, sign_up)", "category": "analytics", "tool_hint": "GA4", "order": 3},
            # GSC
            {"title": "Verificar GSC — impressões, cliques, CTR, posição", "category": "seo", "tool_hint": "GSC", "order": 10},
            {"title": "Identificar novas queries no Search Console", "category": "seo", "tool_hint": "GSC", "order": 11},
            {"title": "Verificar erros de cobertura no GSC", "category": "seo", "tool_hint": "GSC", "order": 12},
            {"title": "Solicitar indexação de páginas novas", "category": "seo", "tool_hint": "GSC", "order": 13},
            # Content
            {"title": "Publicar 1-2 blog posts novos", "category": "content", "tool_hint": "RankPulse", "order": 20},
            {"title": "Revisar e otimizar meta titles/descriptions", "category": "content", "tool_hint": "RankPulse", "order": 21},
            {"title": "Verificar internal linking nos posts", "category": "content", "tool_hint": "Manual", "order": 22},
            # Technical
            {"title": "Verificar robots.txt e sitemap.xml", "category": "technical", "tool_hint": "Navegador", "order": 30},
            {"title": "Testar Core Web Vitals (PageSpeed Insights)", "category": "technical", "tool_hint": "PSI", "order": 31},
            {"title": "Verificar erros 404 e redirects", "category": "technical", "tool_hint": "GSC", "order": 32},
            # Reporting
            {"title": "Preencher relatório semanal no RankPulse", "category": "reporting", "tool_hint": "RankPulse", "order": 40},
            {"title": "Atualizar KPIs e comparar com metas", "category": "reporting", "tool_hint": "RankPulse", "order": 41},
        ]

        for item_data in items:
            obj, item_created = ChecklistTemplateItem.objects.update_or_create(
                template=template,
                title=item_data["title"],
                defaults={
                    "category": item_data["category"],
                    "tool_hint": item_data["tool_hint"],
                    "order": item_data["order"],
                },
            )
            status = "+" if item_created else "="
            self.stdout.write(f"  {status} {obj}")

        self.stdout.write(self.style.SUCCESS(f"\nTemplate com {template.items.count()} items."))
