"""Core models — Sites managed by the traffic system."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Site(models.Model):
    """A website managed by Trafic Provider."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sites",
        verbose_name="Proprietário",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200, verbose_name="Nome do Site")
    domain = models.CharField(max_length=253, unique=True, verbose_name="Domínio")
    url = models.URLField(verbose_name="URL Base")
    description = models.TextField(blank=True, verbose_name="Descrição")

    # GA4
    ga4_measurement_id = models.CharField(
        max_length=30, blank=True, verbose_name="GA4 Measurement ID",
        help_text="Ex: G-BCGGTGQJR9",
    )
    ga4_api_secret = models.CharField(
        max_length=100, blank=True, verbose_name="GA4 API Secret",
        help_text="Measurement Protocol API secret",
    )
    ga4_property_id = models.CharField(
        max_length=30, blank=True, verbose_name="GA4 Property ID",
        help_text="Para GA4 Data API (reporting)",
    )

    # Google Search Console
    gsc_verified = models.BooleanField(default=False, verbose_name="GSC Verificado")
    gsc_site_url = models.URLField(blank=True, verbose_name="GSC Site URL")

    # SEO basics
    sitemap_url = models.URLField(blank=True, verbose_name="Sitemap URL")
    robots_txt_url = models.URLField(blank=True, verbose_name="robots.txt URL")

    # Status
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site"
        verbose_name_plural = "Sites"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.domain})"


class GA4EventDefinition(models.Model):
    """Definition of a GA4 event to track for a site."""

    PRIORITY_CHOICES = [
        ("critical", "Crítica"),
        ("high", "Alta"),
        ("medium", "Média"),
        ("low", "Baixa"),
    ]

    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name="event_definitions",
    )
    event_name = models.CharField(
        max_length=100, verbose_name="Nome do Evento",
        help_text="Ex: sign_up, generate_lead, purchase",
    )
    description = models.TextField(blank=True, verbose_name="Descrição")
    trigger_page = models.CharField(
        max_length=500, blank=True, verbose_name="Página de Disparo",
        help_text="Template ou URL onde o evento deve ser disparado",
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium",
    )
    js_snippet = models.TextField(
        blank=True, verbose_name="Código JavaScript",
        help_text="Snippet gtag() para copiar no template",
    )
    server_side = models.BooleanField(
        default=False, verbose_name="Server-Side (Measurement Protocol)",
    )
    parameters = models.JSONField(
        default=dict, blank=True, verbose_name="Parâmetros",
        help_text="Parâmetros padrão do evento em JSON",
    )
    is_conversion = models.BooleanField(
        default=False, verbose_name="É evento de conversão (Key Event)",
    )
    is_implemented = models.BooleanField(
        default=False, verbose_name="Implementado",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Definição de Evento GA4"
        verbose_name_plural = "Definições de Eventos GA4"
        unique_together = ["site", "event_name"]
        ordering = ["site", "priority", "event_name"]

    def __str__(self) -> str:
        status = "✅" if self.is_implemented else "⬜"
        return f"{status} {self.event_name} ({self.site.name})"


class KPIGoal(models.Model):
    """KPI goal/target for a site at a specific time horizon."""

    PERIOD_CHOICES = [
        ("month_1", "Mês 1"),
        ("month_3", "Mês 3"),
        ("month_6", "Mês 6"),
        ("month_12", "Mês 12"),
    ]

    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name="kpi_goals",
    )
    metric_name = models.CharField(
        max_length=200, verbose_name="Nome da Métrica",
        help_text="Ex: Sessões Orgânicas, Sign-ups, Receita Orgânica",
    )
    source = models.CharField(
        max_length=100, verbose_name="Fonte",
        help_text="Ex: GA4, GSC, Admin",
    )
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    target_value = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Meta",
    )
    current_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Valor Atual",
    )
    unit = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Ex: R$, %, unidades",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Meta de KPI"
        verbose_name_plural = "Metas de KPI"
        ordering = ["site", "period", "metric_name"]

    def __str__(self) -> str:
        return f"{self.metric_name} ({self.get_period_display()}) — {self.site.name}"

    @property
    def progress_pct(self) -> float:
        """Return completion percentage."""
        if self.target_value == 0:
            return 0.0
        return float(min((self.current_value / self.target_value) * 100, 100))


class WeeklySnapshot(models.Model):
    """Weekly traffic snapshot for a site."""

    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name="weekly_snapshots",
    )
    week_start = models.DateField(verbose_name="Início da Semana")
    week_end = models.DateField(verbose_name="Fim da Semana")

    # GA4 metrics
    organic_sessions = models.IntegerField(default=0, verbose_name="Sessões Orgânicas")
    total_sessions = models.IntegerField(default=0, verbose_name="Sessões Totais")
    signups = models.IntegerField(default=0, verbose_name="Sign-ups")
    purchases = models.IntegerField(default=0, verbose_name="Compras")
    revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Receita (R$)",
    )

    # GSC metrics
    gsc_impressions = models.IntegerField(default=0, verbose_name="Impressões GSC")
    gsc_clicks = models.IntegerField(default=0, verbose_name="Cliques GSC")
    gsc_ctr = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="CTR (%)",
    )
    gsc_position = models.DecimalField(
        max_digits=5, decimal_places=1, default=0, verbose_name="Posição Média",
    )
    keywords_top10 = models.IntegerField(default=0, verbose_name="Keywords Top 10")

    # Content metrics
    posts_published = models.IntegerField(default=0, verbose_name="Posts Publicados")
    backlinks = models.IntegerField(default=0, verbose_name="Backlinks")

    # Notes
    highlights = models.TextField(blank=True, verbose_name="Destaques")
    issues = models.TextField(blank=True, verbose_name="Problemas")
    next_steps = models.TextField(blank=True, verbose_name="Próximos Passos")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Snapshot Semanal"
        verbose_name_plural = "Snapshots Semanais"
        unique_together = ["site", "week_start"]
        ordering = ["-week_start"]

    def __str__(self) -> str:
        return f"{self.site.name} — Semana {self.week_start}"
