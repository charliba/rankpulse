"""Stripe payment models — Subscription and PaymentHistory."""
import uuid
from django.conf import settings
from django.db import models


class Subscription(models.Model):
    """Assinatura do usuário — gerencia planos via Stripe."""

    STATUS_CHOICES = [
        ("trialing", "Período de Teste"),
        ("active", "Ativa"),
        ("past_due", "Pagamento Atrasado"),
        ("canceled", "Cancelada"),
        ("unpaid", "Não Paga"),
    ]
    INTERVAL_CHOICES = [
        ("month", "Mensal"),
        ("year", "Anual"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="subscription", verbose_name="Usuário",
    )
    plan = models.CharField(max_length=20, default="starter", verbose_name="Plano")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="trialing")
    billing_interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default="month")

    # Stripe IDs
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)

    # Values
    price_cents = models.IntegerField(default=0, verbose_name="Valor (centavos)")
    currency = models.CharField(max_length=3, default="BRL")

    # Period
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.plan} ({self.status})"


class PaymentHistory(models.Model):
    """Histórico de pagamentos processados pelo Stripe."""

    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("paid", "Pago"),
        ("failed", "Falhou"),
        ("refunded", "Reembolsado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE,
        related_name="payments", verbose_name="Assinatura",
    )
    amount_cents = models.IntegerField(verbose_name="Valor (centavos)")
    currency = models.CharField(max_length=3, default="BRL")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subscription.user} — R${self.amount_cents/100:.2f} ({self.status})"
