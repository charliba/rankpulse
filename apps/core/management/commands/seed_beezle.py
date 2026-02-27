"""Management command to seed Beezle.io as the first managed site."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.models import GA4EventDefinition, KPIGoal, Site


class Command(BaseCommand):
    help = "Seed the database with Beezle.io site data, GA4 events, and KPI goals."

    def handle(self, *args, **options) -> None:
        site, created = Site.objects.update_or_create(
            domain="beezle.io",
            defaults={
                "name": "Beezle",
                "url": "https://beezle.io",
                "description": "Plataforma de programas de indicação (referral programs). "
                "Permite criar, gerenciar e escalar programas com influenciadores e embaixadores.",
                "ga4_measurement_id": "G-BCGGTGQJR9",
                "ga4_api_secret": "",
                "ga4_property_id": "",
                "gsc_verified": True,
                "gsc_site_url": "https://beezle.io",
                "sitemap_url": "https://beezle.io/sitemap.xml",
                "robots_txt_url": "https://beezle.io/robots.txt",
                "is_active": True,
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} site: {site}"))

        # GA4 Events
        events = [
            {
                "event_name": "sign_up",
                "description": "Novo cadastro de empresa na plataforma",
                "trigger_page": "templates/auth/register.html",
                "priority": "critical",
                "is_conversion": True,
                "is_implemented": True,
                "server_side": False,
                "parameters": {"method": "email"},
                "js_snippet": "gtag('event', 'sign_up', {method: 'email'});",
            },
            {
                "event_name": "generate_lead",
                "description": "Empresa criada com sucesso (trial started)",
                "trigger_page": "templates/company/create.html",
                "priority": "critical",
                "is_conversion": True,
                "is_implemented": True,
                "server_side": False,
                "parameters": {"value": 49, "currency": "BRL"},
                "js_snippet": "gtag('event', 'generate_lead', {value: 49, currency: 'BRL'});",
            },
            {
                "event_name": "purchase",
                "description": "Pagamento confirmado via Stripe webhook",
                "trigger_page": "webhooks/views.py (stripe_webhook)",
                "priority": "critical",
                "is_conversion": True,
                "is_implemented": True,
                "server_side": True,
                "parameters": {"transaction_id": "", "value": 0, "currency": "BRL"},
                "js_snippet": "",
            },
            {
                "event_name": "login",
                "description": "Usuário fez login",
                "trigger_page": "templates/auth/login.html",
                "priority": "medium",
                "is_conversion": False,
                "is_implemented": True,
                "server_side": False,
                "parameters": {"method": "email"},
                "js_snippet": "gtag('event', 'login', {method: 'email'});",
            },
            {
                "event_name": "view_item",
                "description": "Visualização da página de planos",
                "trigger_page": "templates/company/plans.html",
                "priority": "high",
                "is_conversion": False,
                "is_implemented": True,
                "server_side": False,
                "parameters": {"item_name": "plans_page"},
                "js_snippet": "gtag('event', 'view_item', {item_name: 'plans_page'});",
            },
            {
                "event_name": "begin_checkout",
                "description": "Usuário clicou para assinar um plano",
                "trigger_page": "templates/vendas/js_checkout.html",
                "priority": "high",
                "is_conversion": True,
                "is_implemented": True,
                "server_side": False,
                "parameters": {"plan": "", "value": 0, "currency": "BRL"},
                "js_snippet": "gtag('event', 'begin_checkout', {value: price, currency: 'BRL'});",
            },
            {
                "event_name": "share",
                "description": "Embaixador compartilhou link",
                "trigger_page": "templates/embaixador/links.html",
                "priority": "medium",
                "is_conversion": False,
                "is_implemented": False,
                "server_side": False,
                "parameters": {"method": "link_copy", "content_type": "referral_link"},
                "js_snippet": "gtag('event', 'share', {method: 'link_copy', content_type: 'referral_link'});",
            },
        ]

        for evt_data in events:
            obj, created = GA4EventDefinition.objects.update_or_create(
                site=site,
                event_name=evt_data["event_name"],
                defaults=evt_data,
            )
            status = "+" if created else "="
            self.stdout.write(f"  {status} {obj}")

        # KPI Goals
        kpis = [
            {"metric_name": "Sessões Orgânicas/mês", "unit": "sessões", "period": "month_1", "target_value": 200},
            {"metric_name": "Sessões Orgânicas/mês", "unit": "sessões", "period": "month_3", "target_value": 1000},
            {"metric_name": "Sessões Orgânicas/mês", "unit": "sessões", "period": "month_6", "target_value": 5000},
            {"metric_name": "Sessões Orgânicas/mês", "unit": "sessões", "period": "month_12", "target_value": 20000},
            {"metric_name": "Keywords Top 10", "unit": "keywords", "period": "month_3", "target_value": 10},
            {"metric_name": "Keywords Top 10", "unit": "keywords", "period": "month_6", "target_value": 30},
            {"metric_name": "Keywords Top 10", "unit": "keywords", "period": "month_12", "target_value": 100},
            {"metric_name": "Sign-ups Orgânicos/mês", "unit": "sign-ups", "period": "month_3", "target_value": 5},
            {"metric_name": "Sign-ups Orgânicos/mês", "unit": "sign-ups", "period": "month_6", "target_value": 20},
            {"metric_name": "Sign-ups Orgânicos/mês", "unit": "sign-ups", "period": "month_12", "target_value": 100},
            {"metric_name": "Blog Posts Publicados", "unit": "posts", "period": "month_1", "target_value": 4},
            {"metric_name": "Blog Posts Publicados", "unit": "posts", "period": "month_3", "target_value": 12},
            {"metric_name": "Blog Posts Publicados", "unit": "posts", "period": "month_6", "target_value": 30},
        ]

        for kpi_data in kpis:
            obj, created = KPIGoal.objects.update_or_create(
                site=site,
                metric_name=kpi_data["metric_name"],
                period=kpi_data["period"],
                defaults={
                    "unit": kpi_data["unit"],
                    "target_value": kpi_data["target_value"],
                },
            )
            status = "+" if created else "="
            self.stdout.write(f"  {status} {obj}")

        self.stdout.write(self.style.SUCCESS("\nSeed Beezle concluído!"))
