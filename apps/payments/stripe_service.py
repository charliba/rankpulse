"""Stripe service — webhook signature verification and event handlers."""
import logging
import stripe
from datetime import datetime
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")


def verify_webhook_signature(payload, sig_header, webhook_secret):
    """Verify Stripe webhook signature. Returns event dict or None."""
    try:
        return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning("Webhook signature verification failed: %s", e)
        return None


def create_checkout_session(user, price_id, success_url, cancel_url):
    """Create a Stripe Checkout Session for subscription."""
    from .models import Subscription

    sub, _ = Subscription.objects.get_or_create(user=user)
    if not sub.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, name=user.get_full_name() or user.username)
        sub.stripe_customer_id = customer.id
        sub.save(update_fields=["stripe_customer_id"])

    return stripe.checkout.Session.create(
        customer=sub.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        locale="pt-BR",
        allow_promotion_codes=True,
        metadata={"user_id": str(user.pk)},
    )


def create_billing_portal_session(user, return_url):
    """Create Stripe Billing Portal session for self-service management."""
    from .models import Subscription

    sub = Subscription.objects.filter(user=user).first()
    if not sub or not sub.stripe_customer_id:
        return None
    return stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=return_url,
    )


# ── Webhook handlers ────────────────────────────────────

def handle_checkout_completed(data_object):
    from .models import Subscription
    customer_id = data_object.get("customer", "")
    subscription_id = data_object.get("subscription", "")
    if not customer_id:
        return
    sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
    if sub and subscription_id:
        sub.stripe_subscription_id = subscription_id
        sub.status = "active"
        sub.save(update_fields=["stripe_subscription_id", "status", "updated_at"])
        logger.info("Checkout completed for customer %s", customer_id)


def handle_subscription_created(data_object):
    from .models import Subscription
    customer_id = data_object.get("customer", "")
    sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
    if not sub:
        return
    sub.stripe_subscription_id = data_object.get("id", "")
    sub.status = data_object.get("status", "active")
    _sync_period(sub, data_object)
    sub.save()
    logger.info("Subscription created: %s", sub.stripe_subscription_id)


def handle_subscription_updated(data_object):
    from .models import Subscription
    customer_id = data_object.get("customer", "")
    sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
    if not sub:
        return
    sub.status = data_object.get("status", sub.status)
    _sync_period(sub, data_object)
    sub.save()
    logger.info("Subscription updated: %s → %s", sub.stripe_subscription_id, sub.status)


def handle_subscription_deleted(data_object):
    from .models import Subscription
    customer_id = data_object.get("customer", "")
    sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
    if not sub:
        return
    sub.status = "canceled"
    sub.canceled_at = timezone.now()
    sub.save(update_fields=["status", "canceled_at", "updated_at"])
    logger.info("Subscription deleted: %s", sub.stripe_subscription_id)


def handle_payment_succeeded(data_object):
    from .models import Subscription, PaymentHistory
    customer_id = data_object.get("customer", "")
    sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
    if not sub:
        return
    invoice_id = data_object.get("id", "")
    if PaymentHistory.objects.filter(stripe_invoice_id=invoice_id).exists():
        return  # Idempotency
    PaymentHistory.objects.create(
        subscription=sub,
        amount_cents=data_object.get("amount_paid", 0),
        currency=data_object.get("currency", "brl").upper(),
        status="paid",
        stripe_invoice_id=invoice_id,
        stripe_payment_intent_id=data_object.get("payment_intent", ""),
        description=f"Fatura {invoice_id}",
        paid_at=timezone.now(),
    )
    if sub.status != "active":
        sub.status = "active"
        sub.save(update_fields=["status", "updated_at"])
    logger.info("Payment succeeded: invoice %s", invoice_id)


def handle_payment_failed(data_object):
    from .models import Subscription, PaymentHistory
    customer_id = data_object.get("customer", "")
    sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
    if not sub:
        return
    invoice_id = data_object.get("id", "")
    if PaymentHistory.objects.filter(stripe_invoice_id=invoice_id).exists():
        return
    PaymentHistory.objects.create(
        subscription=sub,
        amount_cents=data_object.get("amount_due", 0),
        currency=data_object.get("currency", "brl").upper(),
        status="failed",
        stripe_invoice_id=invoice_id,
        description=f"Fatura falhou: {invoice_id}",
    )
    sub.status = "past_due"
    sub.save(update_fields=["status", "updated_at"])
    logger.info("Payment failed: invoice %s", invoice_id)


def _sync_period(sub, data):
    """Sync billing period timestamps from Stripe data."""
    period_start = data.get("current_period_start")
    period_end = data.get("current_period_end")
    if period_start:
        sub.current_period_start = datetime.fromtimestamp(period_start, tz=timezone.utc)
    if period_end:
        sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
