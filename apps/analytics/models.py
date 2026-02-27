"""Analytics models — Event logs, GSC data, GA4 reports."""
from __future__ import annotations

from django.db import models


class GA4EventLog(models.Model):
    """Log of GA4 events sent via Measurement Protocol."""

    STATUS_CHOICES = [
        ("sent", "Enviado"),
        ("validated", "Validado"),
        ("failed", "Falhou"),
    ]

    site = models.ForeignKey(
        "core.Site", on_delete=models.CASCADE, related_name="ga4_event_logs",
    )
    event_name = models.CharField(max_length=100, verbose_name="Evento")
    client_id = models.CharField(max_length=200, verbose_name="Client ID")
    parameters = models.JSONField(default=dict, verbose_name="Parâmetros")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de Evento GA4"
        verbose_name_plural = "Logs de Eventos GA4"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["site", "-created_at"]),
            models.Index(fields=["event_name", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_name} → {self.status} ({self.created_at:%Y-%m-%d %H:%M})"


class SearchConsoleData(models.Model):
    """Daily Google Search Console data (queries + pages)."""

    site = models.ForeignKey(
        "core.Site", on_delete=models.CASCADE, related_name="gsc_data",
    )
    date = models.DateField(verbose_name="Data")
    query = models.CharField(max_length=500, blank=True, verbose_name="Query")
    page = models.URLField(blank=True, verbose_name="Página")
    country = models.CharField(max_length=5, blank=True, default="BRA")
    device = models.CharField(max_length=20, blank=True)  # DESKTOP, MOBILE, TABLET

    clicks = models.IntegerField(default=0, verbose_name="Cliques")
    impressions = models.IntegerField(default=0, verbose_name="Impressões")
    ctr = models.DecimalField(max_digits=6, decimal_places=4, default=0, verbose_name="CTR")
    position = models.DecimalField(
        max_digits=6, decimal_places=1, default=0, verbose_name="Posição",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dados Search Console"
        verbose_name_plural = "Dados Search Console"
        ordering = ["-date", "-clicks"]
        indexes = [
            models.Index(fields=["site", "-date"]),
            models.Index(fields=["query"]),
            models.Index(fields=["page"]),
        ]

    def __str__(self) -> str:
        return f"{self.query[:60]} | {self.clicks} clicks ({self.date})"


class GA4Report(models.Model):
    """Aggregated GA4 reporting data fetched via Data API."""

    REPORT_TYPES = [
        ("traffic", "Aquisição de Tráfego"),
        ("engagement", "Engajamento"),
        ("conversions", "Conversões"),
        ("pages", "Páginas"),
    ]

    site = models.ForeignKey(
        "core.Site", on_delete=models.CASCADE, related_name="ga4_reports",
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    date_start = models.DateField(verbose_name="Data Início")
    date_end = models.DateField(verbose_name="Data Fim")
    data = models.JSONField(default=dict, verbose_name="Dados do Relatório")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Relatório GA4"
        verbose_name_plural = "Relatórios GA4"
        ordering = ["-date_end"]

    def __str__(self) -> str:
        return f"{self.get_report_type_display()} {self.date_start} → {self.date_end}"
