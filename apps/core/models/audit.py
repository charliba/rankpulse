"""Core models — AuditReport, AuditRecommendation, AuditConfig, RecommendationNote."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from .project import Project


class AuditReport(models.Model):
    """AI-generated audit report for a project's campaigns."""

    STATUS_CHOICES = [("running", "Em Execução"), ("done", "Concluído"), ("error", "Erro")]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="audit_reports", verbose_name="Projeto")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="running")
    progress_step = models.CharField(max_length=50, blank=True, verbose_name="Etapa Atual", help_text="Etapa atual do processamento assíncrono")
    business_summary = models.TextField(blank=True, verbose_name="Resumo do Negócio")
    overall_score = models.IntegerField(null=True, blank=True, verbose_name="Score Geral (0-100)")
    overall_analysis = models.TextField(blank=True, verbose_name="Análise Geral")
    raw_data_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Snapshot dos Dados")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Relatório de Auditoria IA"
        verbose_name_plural = "Relatórios de Auditoria IA"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Auditoria #{self.id} — {self.project.name} ({self.get_status_display()})"


class AuditRecommendation(models.Model):
    """Individual AI recommendation with one-click apply capability."""

    PLATFORM_CHOICES = [("google_ads", "Google Ads"), ("meta_ads", "Meta Ads"), ("seo", "SEO / GSC"), ("general", "Geral")]
    IMPACT_CHOICES = [("critical", "Crítico"), ("high", "Alto"), ("medium", "Médio"), ("low", "Baixo")]
    STATUS_CHOICES = [("pending", "Pendente"), ("applied", "Aplicado"), ("dismissed", "Descartado"), ("failed", "Falhou")]
    CATEGORY_CHOICES = [
        ("negative_keywords", "Palavras-Chave Negativas"), ("sitelinks", "Sitelinks"),
        ("callouts", "Callouts / Extensões"), ("ad_copy", "Texto do Anúncio"),
        ("bidding", "Estratégia de Lances"), ("targeting", "Segmentação de Público"),
        ("audience_age", "Faixa Etária"), ("audience_interests", "Interesses"),
        ("audience_geo", "Geolocalização"), ("ad_schedule", "Agendamento"),
        ("keywords", "Palavras-Chave"), ("quality_score", "Quality Score"),
        ("campaign_structure", "Estrutura de Campanha"), ("creative", "Criativos"),
        ("landing_page", "Landing Page"), ("conversion_tracking", "Rastreamento de Conversão"),
        ("indexing", "Indexação"), ("content_gap", "Gap de Conteúdo"), ("other", "Outro"),
    ]

    report = models.ForeignKey(AuditReport, on_delete=models.CASCADE, related_name="recommendations", verbose_name="Relatório")
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="other")
    impact = models.CharField(max_length=10, choices=IMPACT_CHOICES, default="medium")
    title = models.CharField(max_length=300, verbose_name="Título")
    explanation = models.TextField(verbose_name="Explicação Detalhada")
    action_description = models.TextField(blank=True, verbose_name="Ação Proposta")
    action_payload = models.JSONField(default=dict, blank=True, verbose_name="Payload da Ação", help_text="Dados estruturados para execução automática")
    can_auto_apply = models.BooleanField(default=False, verbose_name="Aplicável Automaticamente")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    apply_result = models.JSONField(default=dict, blank=True, verbose_name="Resultado da Aplicação")
    applied_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Verificado em")
    verification_result = models.JSONField(default=dict, blank=True, verbose_name="Resultado da Verificação")
    campaign_id = models.CharField(max_length=100, blank=True, verbose_name="ID da Campanha")
    campaign_name = models.CharField(max_length=300, blank=True, verbose_name="Nome da Campanha")
    estimated_points = models.IntegerField(default=0, verbose_name="Pontos Estimados", help_text="Pontos que o usuário ganha ao aplicar esta recomendação")

    class Meta:
        verbose_name = "Recomendação de Auditoria"
        verbose_name_plural = "Recomendações de Auditoria"
        ordering = ["report", "impact", "platform"]

    def __str__(self) -> str:
        return f"[{self.get_impact_display()}] {self.title}"


class AuditConfig(models.Model):
    """Per-project AI audit configuration — toggles which data sources and analysis dimensions the audit engine should include."""

    DEPTH_CHOICES = [("quick", "Rápida (resumo)"), ("standard", "Padrão"), ("deep", "Profunda (detalhada)")]
    LANGUAGE_CHOICES = [("pt-BR", "Português (BR)"), ("en", "English"), ("es", "Español")]

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="audit_config", verbose_name="Projeto")

    # Data Sources
    source_meta_ads = models.BooleanField(default=True, verbose_name="Meta Ads")
    source_google_ads = models.BooleanField(default=True, verbose_name="Google Ads")
    source_seo = models.BooleanField(default=True, verbose_name="SEO / Search Console")
    source_ga4 = models.BooleanField(default=True, verbose_name="GA4 Analytics")

    # Meta Ads Dimensions
    meta_campaign_structure = models.BooleanField(default=True, verbose_name="Estrutura de Campanhas")
    meta_audience_targeting = models.BooleanField(default=True, verbose_name="Segmentação de Público")
    meta_creatives = models.BooleanField(default=True, verbose_name="Criativos e Copies")
    meta_budget_bidding = models.BooleanField(default=True, verbose_name="Orçamento e Lances")
    meta_placements = models.BooleanField(default=True, verbose_name="Posicionamentos")
    meta_demographics = models.BooleanField(default=True, verbose_name="Demografia")
    meta_ad_performance = models.BooleanField(default=True, verbose_name="Performance por Anúncio")
    meta_conversion_tracking = models.BooleanField(default=True, verbose_name="Rastreamento de Conversão")

    # Google Ads Dimensions
    google_campaign_structure = models.BooleanField(default=True, verbose_name="Estrutura de Campanhas")
    google_keywords = models.BooleanField(default=True, verbose_name="Palavras-Chave")
    google_search_terms = models.BooleanField(default=True, verbose_name="Termos de Busca")
    google_ad_copies = models.BooleanField(default=True, verbose_name="Textos dos Anúncios")
    google_extensions = models.BooleanField(default=True, verbose_name="Extensões (Sitelinks, Callouts)")
    google_bidding = models.BooleanField(default=True, verbose_name="Estratégia de Lances")
    google_quality_score = models.BooleanField(default=True, verbose_name="Quality Score")
    google_geo_targeting = models.BooleanField(default=True, verbose_name="Geolocalização")
    google_conversion_tracking = models.BooleanField(default=True, verbose_name="Rastreamento de Conversão")

    # GA4 Dimensions
    ga4_traffic_sources = models.BooleanField(default=True, verbose_name="Fontes de Tráfego")
    ga4_top_pages = models.BooleanField(default=True, verbose_name="Top Páginas")
    ga4_conversions = models.BooleanField(default=True, verbose_name="Eventos de Conversão")
    ga4_demographics = models.BooleanField(default=True, verbose_name="Demografia")
    ga4_devices = models.BooleanField(default=True, verbose_name="Dispositivos")
    ga4_organic = models.BooleanField(default=True, verbose_name="Tráfego Orgânico")

    # SEO Dimensions
    seo_top_queries = models.BooleanField(default=True, verbose_name="Top Queries")
    seo_top_pages = models.BooleanField(default=True, verbose_name="Top Páginas")
    seo_indexing = models.BooleanField(default=True, verbose_name="Indexação")

    # Cross-platform
    cross_platform_synthesis = models.BooleanField(default=True, verbose_name="Síntese Cross-Platform")
    brand_dna_context = models.BooleanField(default=True, verbose_name="Contexto Brand DNA")

    # AI Settings
    ai_depth = models.CharField(max_length=10, choices=DEPTH_CHOICES, default="standard", verbose_name="Profundidade da Análise")
    ai_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="pt-BR", verbose_name="Idioma da Análise")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Auditoria"
        verbose_name_plural = "Configurações de Auditoria"

    def __str__(self) -> str:
        return f"Audit Config — {self.project.name}"


class RecommendationNote(models.Model):
    """User observation on a specific recommendation."""

    recommendation = models.ForeignKey(AuditRecommendation, on_delete=models.CASCADE, related_name="notes", verbose_name="Recomendação")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendation_notes", verbose_name="Usuário")
    text = models.TextField(verbose_name="Observação")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Observação de Recomendação"
        verbose_name_plural = "Observações de Recomendações"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Nota #{self.pk} — {self.recommendation.title[:40]}"
