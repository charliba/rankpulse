"""SEO models — Audits, page scores, keyword tracking."""
from __future__ import annotations

from django.db import models


class SEOAudit(models.Model):
    """Full SEO audit of a managed site."""

    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("running", "Executando"),
        ("completed", "Concluído"),
        ("failed", "Falhou"),
    ]

    site = models.ForeignKey(
        "core.Site", on_delete=models.CASCADE, related_name="seo_audits",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    overall_score = models.IntegerField(
        default=0, verbose_name="Score Geral (0-100)",
    )

    # Category scores
    meta_score = models.IntegerField(default=0, verbose_name="Meta Tags Score")
    content_score = models.IntegerField(default=0, verbose_name="Conteúdo Score")
    technical_score = models.IntegerField(default=0, verbose_name="Técnico Score")
    performance_score = models.IntegerField(default=0, verbose_name="Performance Score")
    structured_data_score = models.IntegerField(default=0, verbose_name="Dados Estruturados Score")

    # Summary
    pages_crawled = models.IntegerField(default=0)
    issues_critical = models.IntegerField(default=0)
    issues_warning = models.IntegerField(default=0)
    issues_info = models.IntegerField(default=0)
    recommendations = models.JSONField(default=list, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Auditoria SEO"
        verbose_name_plural = "Auditorias SEO"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Audit {self.site.name} — {self.overall_score}/100 ({self.created_at:%Y-%m-%d})"


class PageScore(models.Model):
    """SEO score for an individual page within an audit."""

    SEVERITY_CHOICES = [
        ("ok", "OK"),
        ("info", "Info"),
        ("warning", "Atenção"),
        ("critical", "Crítico"),
    ]

    audit = models.ForeignKey(
        SEOAudit, on_delete=models.CASCADE, related_name="page_scores",
    )
    url = models.URLField(verbose_name="URL da Página")
    score = models.IntegerField(default=0, verbose_name="Score (0-100)")

    # Meta tags
    has_title = models.BooleanField(default=False)
    title_length = models.IntegerField(default=0)
    has_meta_description = models.BooleanField(default=False)
    meta_description_length = models.IntegerField(default=0)
    has_canonical = models.BooleanField(default=False)
    has_og_tags = models.BooleanField(default=False)

    # Content
    has_h1 = models.BooleanField(default=False)
    h1_count = models.IntegerField(default=0)
    h2_count = models.IntegerField(default=0)
    word_count = models.IntegerField(default=0)
    has_images_alt = models.BooleanField(default=False)
    images_total = models.IntegerField(default=0)
    images_missing_alt = models.IntegerField(default=0)

    # Technical
    has_structured_data = models.BooleanField(default=False)
    structured_data_types = models.JSONField(default=list, blank=True)
    has_robots_meta = models.BooleanField(default=False)
    is_indexable = models.BooleanField(default=True)
    http_status = models.IntegerField(default=200)
    load_time_ms = models.IntegerField(default=0, verbose_name="Tempo de Carregamento (ms)")

    # Issues found
    issues = models.JSONField(default=list, blank=True, verbose_name="Problemas")

    class Meta:
        verbose_name = "Score de Página"
        verbose_name_plural = "Scores de Páginas"
        ordering = ["score"]

    def __str__(self) -> str:
        return f"{self.url} — {self.score}/100"


class KeywordTracking(models.Model):
    """Track keyword rankings over time."""

    site = models.ForeignKey(
        "core.Site", on_delete=models.CASCADE, related_name="tracked_keywords",
    )
    keyword = models.CharField(max_length=300, verbose_name="Palavra-chave")
    target_url = models.URLField(blank=True, verbose_name="URL Alvo")

    # Current metrics (updated from GSC)
    current_position = models.DecimalField(
        max_digits=6, decimal_places=1, default=0, verbose_name="Posição Atual",
    )
    best_position = models.DecimalField(
        max_digits=6, decimal_places=1, default=0, verbose_name="Melhor Posição",
    )
    impressions_30d = models.IntegerField(default=0, verbose_name="Impressões 30d")
    clicks_30d = models.IntegerField(default=0, verbose_name="Cliques 30d")
    ctr_30d = models.DecimalField(
        max_digits=6, decimal_places=4, default=0, verbose_name="CTR 30d",
    )

    # Tracking
    is_priority = models.BooleanField(default=False, verbose_name="Keyword Prioritária")
    notes = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Keyword Tracking"
        verbose_name_plural = "Keywords Tracking"
        unique_together = ["site", "keyword"]
        ordering = ["current_position"]

    def __str__(self) -> str:
        return f"{self.keyword} → #{self.current_position} ({self.site.name})"
