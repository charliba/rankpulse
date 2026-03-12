"""Core models — AlertRule and AlertEvent."""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from .project import Project


class AlertRule(models.Model):
    """User-defined alert rule for a project metric."""

    METRIC_CHOICES = [
        ("sessions", "Sessões Orgânicas"), ("gsc_clicks", "Cliques GSC"),
        ("gsc_impressions", "Impressões GSC"), ("gsc_position", "Posição Média GSC"),
        ("ads_spend", "Gasto Google Ads"), ("ads_clicks", "Cliques Google Ads"),
        ("ads_cpc", "CPC Google Ads"), ("ads_conversions", "Conversões Google Ads"),
        ("meta_spend", "Gasto Meta Ads"), ("meta_clicks", "Cliques Meta Ads"),
        ("meta_cpc", "CPC Meta Ads"),
    ]
    CONDITION_CHOICES = [
        ("gt", "Maior que"), ("lt", "Menor que"),
        ("change_up", "Subiu mais que (%)"), ("change_down", "Caiu mais que (%)"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="alert_rules", verbose_name="Projeto")
    name = models.CharField(max_length=200, verbose_name="Nome do Alerta")
    metric = models.CharField(max_length=30, choices=METRIC_CHOICES, verbose_name="Métrica")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, verbose_name="Condição")
    threshold = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Limite", help_text="Valor absoluto ou percentual conforme condição")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    notify_email = models.BooleanField(default=False, verbose_name="Notificar por Email")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Regra de Alerta"
        verbose_name_plural = "Regras de Alerta"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_metric_display()} {self.get_condition_display()} {self.threshold})"


class AlertEvent(models.Model):
    """A triggered alert event."""

    SEVERITY_CHOICES = [("info", "Info"), ("warning", "Aviso"), ("critical", "Crítico")]

    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name="events", verbose_name="Regra")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="warning")
    current_value = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor Atual")
    previous_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Valor Anterior")
    message = models.TextField(verbose_name="Mensagem")
    is_read = models.BooleanField(default=False, verbose_name="Lido")
    triggered_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Evento de Alerta"
        verbose_name_plural = "Eventos de Alerta"
        ordering = ["-triggered_at"]

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule.name} — {self.triggered_at:%d/%m %H:%M}"
