"""Add GA4 data types to DataSnapshot choices and create AuditConfig model."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_brandprofile_datasnapshot_project_goals"),
    ]

    operations = [
        # DataSnapshot.data_type now includes GA4 types — choices are enforced
        # at the Python level only, so no DB schema change needed for that field.

        # New AuditConfig model
        migrations.CreateModel(
            name="AuditConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                # Data Sources
                ("source_meta_ads", models.BooleanField(default=True, verbose_name="Meta Ads")),
                ("source_google_ads", models.BooleanField(default=True, verbose_name="Google Ads")),
                ("source_seo", models.BooleanField(default=True, verbose_name="SEO / Search Console")),
                ("source_ga4", models.BooleanField(default=True, verbose_name="GA4 Analytics")),
                # Meta Ads Dimensions
                ("meta_campaign_structure", models.BooleanField(default=True, verbose_name="Estrutura de Campanhas")),
                ("meta_audience_targeting", models.BooleanField(default=True, verbose_name="Segmentação de Público")),
                ("meta_creatives", models.BooleanField(default=True, verbose_name="Criativos e Copies")),
                ("meta_budget_bidding", models.BooleanField(default=True, verbose_name="Orçamento e Lances")),
                ("meta_placements", models.BooleanField(default=True, verbose_name="Posicionamentos")),
                ("meta_demographics", models.BooleanField(default=True, verbose_name="Demografia")),
                ("meta_ad_performance", models.BooleanField(default=True, verbose_name="Performance por Anúncio")),
                ("meta_conversion_tracking", models.BooleanField(default=True, verbose_name="Rastreamento de Conversão")),
                # Google Ads Dimensions
                ("google_campaign_structure", models.BooleanField(default=True, verbose_name="Estrutura de Campanhas")),
                ("google_keywords", models.BooleanField(default=True, verbose_name="Palavras-Chave")),
                ("google_search_terms", models.BooleanField(default=True, verbose_name="Termos de Busca")),
                ("google_ad_copies", models.BooleanField(default=True, verbose_name="Textos dos Anúncios")),
                ("google_extensions", models.BooleanField(default=True, verbose_name="Extensões (Sitelinks, Callouts)")),
                ("google_bidding", models.BooleanField(default=True, verbose_name="Estratégia de Lances")),
                ("google_quality_score", models.BooleanField(default=True, verbose_name="Quality Score")),
                ("google_geo_targeting", models.BooleanField(default=True, verbose_name="Geolocalização")),
                ("google_conversion_tracking", models.BooleanField(default=True, verbose_name="Rastreamento de Conversão")),
                # GA4 Dimensions
                ("ga4_traffic_sources", models.BooleanField(default=True, verbose_name="Fontes de Tráfego")),
                ("ga4_top_pages", models.BooleanField(default=True, verbose_name="Top Páginas")),
                ("ga4_conversions", models.BooleanField(default=True, verbose_name="Eventos de Conversão")),
                ("ga4_demographics", models.BooleanField(default=True, verbose_name="Demografia")),
                ("ga4_devices", models.BooleanField(default=True, verbose_name="Dispositivos")),
                ("ga4_organic", models.BooleanField(default=True, verbose_name="Tráfego Orgânico")),
                # SEO Dimensions
                ("seo_top_queries", models.BooleanField(default=True, verbose_name="Top Queries")),
                ("seo_top_pages", models.BooleanField(default=True, verbose_name="Top Páginas")),
                ("seo_indexing", models.BooleanField(default=True, verbose_name="Indexação")),
                # Cross-platform
                ("cross_platform_synthesis", models.BooleanField(default=True, verbose_name="Síntese Cross-Platform")),
                ("brand_dna_context", models.BooleanField(default=True, verbose_name="Contexto Brand DNA")),
                # AI Settings
                ("ai_depth", models.CharField(choices=[("quick", "Rápida (resumo)"), ("standard", "Padrão"), ("deep", "Profunda (detalhada)")], default="standard", max_length=10, verbose_name="Profundidade da Análise")),
                ("ai_language", models.CharField(choices=[("pt-BR", "Português (BR)"), ("en", "English"), ("es", "Español")], default="pt-BR", max_length=5, verbose_name="Idioma da Análise")),
                # Timestamps
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                # FK
                ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="audit_config", to="core.project", verbose_name="Projeto")),
            ],
            options={
                "verbose_name": "Configuração de Auditoria",
                "verbose_name_plural": "Configurações de Auditoria",
            },
        ),
    ]
