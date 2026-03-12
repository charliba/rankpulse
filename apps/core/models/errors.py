"""Core models — SystemErrorLog."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class SystemErrorLog(models.Model):
    """Auto-captured system errors and exceptions — visible in developer dashboard."""

    ERROR_TYPE_CHOICES = [
        ("view_error", "Erro em View"), ("api_error", "Erro de API Externa"),
        ("audit_error", "Erro na Auditoria"), ("integration_error", "Erro de Integração"),
        ("unknown", "Desconhecido"),
    ]
    SEVERITY_CHOICES = [
        ("info", "Info"), ("warning", "Aviso"),
        ("error", "Erro"), ("critical", "Crítico"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="error_logs")
    error_type = models.CharField(max_length=20, choices=ERROR_TYPE_CHOICES, default="unknown")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="error")
    error_message = models.TextField(verbose_name="Mensagem")
    traceback = models.TextField(blank=True, verbose_name="Traceback")
    view_name = models.CharField(max_length=200, blank=True, verbose_name="View")
    url_path = models.CharField(max_length=500, blank=True, verbose_name="URL")
    http_method = models.CharField(max_length=10, blank=True)
    request_body = models.TextField(blank=True, verbose_name="Request Body (sanitizado)")
    session_key = models.CharField(max_length=100, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    resolved = models.BooleanField(default=False, verbose_name="Resolvido")
    developer_notes = models.TextField(blank=True, verbose_name="Notas do Desenvolvedor")
    resolution_notes = models.TextField(blank=True, verbose_name="Notas de Resolução")
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="Arquivado em")

    class Meta:
        verbose_name = "Log de Erro do Sistema"
        verbose_name_plural = "Logs de Erros do Sistema"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp", "resolved"]),
            models.Index(fields=["error_type", "-timestamp"]),
        ]

    def __str__(self) -> str:
        return f"[{self.severity}] {self.error_message[:80]} — {self.timestamp:%d/%m %H:%M}"
