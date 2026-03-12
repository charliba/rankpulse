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


# ── Campaign Optimizer ───────────────────────────────────────────

class OptimizerConfig(models.Model):
    """OneClickAds-style optimizer parametrization per channel."""

    MODE_CHOICES = [
        ("monitor", "Monitor (somente leitura)"),
        ("active", "Ativo (executa ações)"),
    ]
    OPTIMIZE_BY_CHOICES = [
        ("cpa", "CPA (Custo por Aquisição)"),
        ("roas", "ROAS (Retorno sobre Gasto)"),
    ]
    PAUSE_BEHAVIOR_CHOICES = [
        ("rigid", "Rígido (pausa imediata)"),
        ("flexible", "Flexível (aguarda mais dados)"),
    ]
    SCALE_BEHAVIOR_CHOICES = [
        ("conservative", "Conservador (+20%)"),
        ("accelerated", "Acelerado (+50%)"),
    ]

    channel = models.OneToOneField(
        Channel, on_delete=models.CASCADE, related_name="optimizer_config",
        verbose_name="Canal",
    )
    enabled = models.BooleanField(default=False, verbose_name="Habilitado")
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="monitor", verbose_name="Modo")
    optimize_by = models.CharField(max_length=5, choices=OPTIMIZE_BY_CHOICES, default="cpa", verbose_name="Otimizar por")
    cpa_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="CPA Máximo (R$)", help_text="Stop loss — pausa se CPA ultrapassar",
    )
    roas_min = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="ROAS Mínimo", help_text="Ex: 2.0 = retorno de 2x",
    )
    sale_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Valor da Venda (R$)", help_text="Para cálculo de ROAS",
    )
    pause_behavior = models.CharField(
        max_length=10, choices=PAUSE_BEHAVIOR_CHOICES, default="rigid",
        verbose_name="Comportamento de Pausa",
    )
    scale_behavior = models.CharField(
        max_length=15, choices=SCALE_BEHAVIOR_CHOICES, default="conservative",
        verbose_name="Comportamento de Escala",
    )
    daily_budget_cap = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Teto Diário por Campanha (R$)",
    )
    monthly_budget_limit = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Limite Mensal da Conta (R$)",
    )
    lookback_days = models.IntegerField(default=1, verbose_name="Dias de Lookback")
    min_spend_to_evaluate = models.DecimalField(
        max_digits=10, decimal_places=2, default=5.0,
        verbose_name="Gasto Mínimo para Avaliar (R$)",
    )
    excluded_campaigns = models.JSONField(
        default=list, blank=True, verbose_name="Campanhas Excluídas (IDs)",
    )
    excluded_ad_sets = models.JSONField(
        default=list, blank=True, verbose_name="Conjuntos Excluídos (IDs)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração do Otimizador"
        verbose_name_plural = "Configurações do Otimizador"

    def __str__(self) -> str:
        return f"Optimizer — {self.channel.name} ({self.get_mode_display()})"


class OptimizerAction(models.Model):
    """Log of actions taken (or proposed) by the optimizer."""

    ACTION_TYPE_CHOICES = [
        ("PAUSED", "Pausado"),
        ("WOULD_PAUSE", "Pausaria (monitor)"),
        ("REACTIVATED", "Reativado"),
        ("WOULD_REACTIVATE", "Reativaria (monitor)"),
        ("SCALED", "Escalonado"),
        ("WOULD_SCALE", "Escalonaria (monitor)"),
        ("PAUSE_FAILED", "Falha ao Pausar"),
        ("REACTIVATE_FAILED", "Falha ao Reativar"),
        ("SCALE_FAILED", "Falha ao Escalonar"),
        ("BUDGET_LIMIT", "Limite de Orçamento"),
        ("SKIPPED", "Ignorado"),
        ("NO_DATA", "Sem Dados"),
    ]
    TARGET_TYPE_CHOICES = [
        ("campaign", "Campanha"),
        ("ad_set", "Conjunto de Anúncios"),
        ("account", "Conta"),
    ]

    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="optimizer_actions",
        verbose_name="Canal",
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES)
    target_type = models.CharField(max_length=10, choices=TARGET_TYPE_CHOICES, default="ad_set")
    target_id = models.CharField(max_length=100, verbose_name="ID do Alvo")
    target_name = models.CharField(max_length=300, verbose_name="Nome do Alvo")
    reason = models.TextField(verbose_name="Motivo")
    details = models.JSONField(default=dict, blank=True, verbose_name="Detalhes")
    mode = models.CharField(max_length=10, default="monitor")
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ação do Otimizador"
        verbose_name_plural = "Ações do Otimizador"
        ordering = ["-executed_at"]

    def __str__(self) -> str:
        return f"[{self.action_type}] {self.target_name} — {self.executed_at:%d/%m %H:%M}"
