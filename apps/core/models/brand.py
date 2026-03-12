"""Core models — BrandProfile and DataSnapshot."""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from .project import Project


class BrandProfile(models.Model):
    """Persistent Brand DNA — stores everything the AI needs to understand the business."""

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="brand_profile", verbose_name="Projeto")

    # Website intelligence
    website_content = models.TextField(blank=True, verbose_name="Conteúdo Estruturado do Site", help_text="Seções extraídas: serviços, sobre, preços, depoimentos")
    website_raw_text = models.TextField(blank=True, verbose_name="Texto Bruto do Site")

    # Social media — Instagram
    instagram_profile = models.JSONField(default=dict, blank=True, verbose_name="Perfil Instagram", help_text="username, bio, followers, media_count, profile_pic_url")
    instagram_posts = models.JSONField(default=list, blank=True, verbose_name="Posts Instagram", help_text="Últimos 25 posts com caption, engagement, media_type")

    # Social media — Facebook
    facebook_page = models.JSONField(default=dict, blank=True, verbose_name="Página Facebook", help_text="name, about, fan_count, category, website")
    facebook_posts = models.JSONField(default=list, blank=True, verbose_name="Posts Facebook", help_text="Últimos 25 posts com message, reactions, shares")

    # AI-generated brand intelligence
    brand_summary = models.TextField(blank=True, verbose_name="Brand DNA (resumo IA)", help_text="Resumo completo da marca gerado pela IA")
    target_audience = models.TextField(blank=True, verbose_name="Público-Alvo Inferido")
    tone_of_voice = models.CharField(max_length=100, blank=True, verbose_name="Tom de Voz", help_text="Ex: formal, informal, técnico, jovem, premium")
    key_services = models.JSONField(default=list, blank=True, verbose_name="Serviços/Produtos", help_text="Lista de serviços ou produtos identificados")
    differentiators = models.TextField(blank=True, verbose_name="Diferenciais Competitivos")

    # Deep crawl results
    discovered_urls = models.JSONField(default=list, blank=True, verbose_name="URLs Descobertas", help_text="Lista de URLs do site descobertas via crawling")
    total_pages_found = models.IntegerField(default=0, verbose_name="Total de Páginas")

    # Refresh timestamps
    last_website_scan = models.DateTimeField(null=True, blank=True)
    last_social_scan = models.DateTimeField(null=True, blank=True)
    last_brand_analysis = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil da Marca"
        verbose_name_plural = "Perfis de Marca"

    def __str__(self) -> str:
        return f"Brand DNA — {self.project.name}"

    def website_needs_refresh(self, max_age_days: int = 7) -> bool:
        if not self.last_website_scan:
            return True
        age = timezone.now() - self.last_website_scan
        return age.total_seconds() > max_age_days * 86400

    def social_needs_refresh(self, max_age_days: int = 3) -> bool:
        if not self.last_social_scan:
            return True
        age = timezone.now() - self.last_social_scan
        return age.total_seconds() > max_age_days * 86400

    def brand_analysis_needs_refresh(self) -> bool:
        if not self.last_brand_analysis:
            return True
        if self.last_website_scan and self.last_website_scan > self.last_brand_analysis:
            return True
        if self.last_social_scan and self.last_social_scan > self.last_brand_analysis:
            return True
        return False


class DataSnapshot(models.Model):
    """Cached API data for a project — avoids re-fetching on every audit."""

    DATA_TYPE_CHOICES = [
        # Meta Ads
        ("meta_campaigns", "Meta Ads — Campanhas"), ("meta_ad_sets", "Meta Ads — Conjuntos de Anúncios"),
        ("meta_ads_creatives", "Meta Ads — Anúncios/Criativos"), ("meta_demographics", "Meta Ads — Demografia"),
        ("meta_placements", "Meta Ads — Posicionamentos"), ("meta_ad_insights", "Meta Ads — Insights por Anúncio"),
        ("meta_account_overview", "Meta Ads — Visão Geral da Conta"), ("meta_campaign_insights", "Meta Ads — Insights por Campanha"),
        # Google Ads
        ("google_campaigns", "Google Ads — Campanhas"), ("google_campaign_details", "Google Ads — Detalhes de Campanhas"),
        ("google_keywords", "Google Ads — Palavras-Chave"), ("google_search_terms", "Google Ads — Termos de Busca"),
        ("google_ad_copies", "Google Ads — Textos dos Anúncios"), ("google_assets", "Google Ads — Extensões"),
        ("google_locations", "Google Ads — Localização"), ("google_ad_groups", "Google Ads — Grupos de Anúncios"),
        ("google_performance", "Google Ads — Performance 30d"),
        # SEO
        ("seo_queries", "SEO — Queries"), ("seo_pages", "SEO — Páginas"), ("seo_daily", "SEO — Totais Diários"),
        # GA4
        ("ga4_overview", "GA4 — Visão Geral"), ("ga4_traffic_sources", "GA4 — Fontes de Tráfego"),
        ("ga4_top_pages", "GA4 — Top Páginas"), ("ga4_organic_traffic", "GA4 — Tráfego Orgânico"),
        ("ga4_conversions", "GA4 — Conversões"), ("ga4_demographics", "GA4 — Demografia"),
        ("ga4_devices", "GA4 — Dispositivos"),
    ]

    TTL_MAP = {
        "meta_campaigns": 24, "meta_ad_sets": 24, "meta_ads_creatives": 12,
        "meta_demographics": 6, "meta_placements": 6, "meta_ad_insights": 6,
        "meta_account_overview": 6, "meta_campaign_insights": 6,
        "google_campaigns": 24, "google_campaign_details": 24, "google_keywords": 12,
        "google_search_terms": 6, "google_ad_copies": 24, "google_assets": 24,
        "google_locations": 24, "google_ad_groups": 24, "google_performance": 6,
        "seo_queries": 24, "seo_pages": 24, "seo_daily": 24,
        "ga4_overview": 12, "ga4_traffic_sources": 12, "ga4_top_pages": 12,
        "ga4_organic_traffic": 12, "ga4_conversions": 12, "ga4_demographics": 24,
        "ga4_devices": 24,
    }

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="data_snapshots", verbose_name="Projeto")
    data_type = models.CharField(max_length=30, choices=DATA_TYPE_CHOICES, verbose_name="Tipo de Dado")
    data = models.JSONField(default=list, verbose_name="Dados Completos")
    record_count = models.IntegerField(default=0, verbose_name="Registros")
    collected_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Expira em")
    is_valid = models.BooleanField(default=True, verbose_name="Válido")

    class Meta:
        verbose_name = "Snapshot de Dados"
        verbose_name_plural = "Snapshots de Dados"
        ordering = ["-collected_at"]
        indexes = [models.Index(fields=["project", "data_type", "-collected_at"])]

    def __str__(self) -> str:
        return f"{self.get_data_type_display()} — {self.project.name} ({self.collected_at:%d/%m %H:%M})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return self.is_valid and not self.is_expired

    @property
    def age_display(self) -> str:
        delta = timezone.now() - self.collected_at
        hours = delta.total_seconds() / 3600
        if hours < 1:
            return f"há {int(delta.total_seconds() / 60)}min"
        if hours < 24:
            return f"há {int(hours)}h"
        return f"há {int(hours / 24)}d"

    @classmethod
    def get_valid(cls, project, data_type: str):
        snap = cls.objects.filter(project=project, data_type=data_type, is_valid=True).first()
        if snap and snap.is_usable:
            return snap
        return None

    @classmethod
    def store(cls, project, data_type: str, data, record_count: int = 0):
        from datetime import timedelta
        ttl_hours = cls.TTL_MAP.get(data_type, 12)
        cls.objects.filter(project=project, data_type=data_type, is_valid=True).update(is_valid=False)
        return cls.objects.create(
            project=project, data_type=data_type, data=data,
            record_count=record_count if record_count else (len(data) if isinstance(data, list) else 1),
            expires_at=timezone.now() + timedelta(hours=ttl_hours),
        )
