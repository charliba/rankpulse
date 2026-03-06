"""Channel models — Traffic channels (Google Ads, Meta Ads, etc.) per project."""
from __future__ import annotations

from django.db import models


class Channel(models.Model):
    """A traffic channel connected to a project (e.g. Google Ads account)."""

    PLATFORM_CHOICES = [
        ("google_ads", "Google Ads"),
        ("meta_ads", "Meta Ads"),
    ]

    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
        related_name="channels",
        verbose_name="Projeto",
    )
    platform = models.CharField(
        max_length=30,
        choices=PLATFORM_CHOICES,
        verbose_name="Plataforma",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Nome do Canal",
        help_text="Ex: 'Google Ads — My Face', 'Meta Ads — Beezle'",
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Canal"
        verbose_name_plural = "Canais"
        unique_together = ["project", "platform"]
        ordering = ["project", "platform"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_platform_display()})"

    @property
    def is_configured(self) -> bool:
        """Check whether minimum credentials are present."""
        try:
            cred = self.credentials
        except ChannelCredential.DoesNotExist:
            return False
        if self.platform == "google_ads":
            return bool(
                cred.customer_id
                and cred.developer_token
                and cred.client_id
                and cred.client_secret
                and cred.refresh_token
            )
        if self.platform == "meta_ads":
            return bool(cred.access_token and cred.account_id)
        return False


class ChannelCredential(models.Model):
    """Credentials for a traffic channel — extensible for multiple platforms."""

    channel = models.OneToOneField(
        Channel,
        on_delete=models.CASCADE,
        related_name="credentials",
        verbose_name="Canal",
    )

    # Google Ads
    customer_id = models.CharField(
        max_length=30, blank=True, verbose_name="Customer ID",
        help_text="Formato: 123-456-7890",
    )
    developer_token = models.CharField(
        max_length=100, blank=True, verbose_name="Developer Token",
    )
    client_id = models.CharField(
        max_length=200, blank=True, verbose_name="OAuth Client ID",
    )
    client_secret = models.CharField(
        max_length=200, blank=True, verbose_name="OAuth Client Secret",
    )
    refresh_token = models.CharField(
        max_length=500, blank=True, verbose_name="OAuth Refresh Token",
    )
    login_customer_id = models.CharField(
        max_length=30, blank=True, verbose_name="Login Customer ID (MCC)",
    )

    # Meta Ads
    access_token = models.CharField(
        max_length=500, blank=True, verbose_name="Access Token",
    )
    account_id = models.CharField(
        max_length=100, blank=True, verbose_name="Ad Account ID",
        help_text="Ex: act_123456789",
    )

    # Extensible
    extra = models.JSONField(
        default=dict, blank=True, verbose_name="Dados Extras",
        help_text="Campos adicionais por plataforma (JSON)",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Credencial de Canal"
        verbose_name_plural = "Credenciais de Canais"

    def __str__(self) -> str:
        return f"Credentials — {self.channel.name}"
