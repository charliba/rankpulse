"""Stripe webhook endpoint."""
import logging
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Receive and process Stripe webhook events."""
    from .stripe_service import (
        verify_webhook_signature,
        handle_checkout_completed,
        handle_subscription_created,
        handle_subscription_updated,
        handle_subscription_deleted,
        handle_payment_succeeded,
        handle_payment_failed,
    )

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return HttpResponse(status=400)

    event = verify_webhook_signature(payload, sig_header, webhook_secret)
    if not event:
        return HttpResponse(status=400)

    event_type = event["type"]
    data_object = event["data"]["object"]
    logger.info("Stripe webhook: type=%s, id=%s", event_type, event["id"])

    handlers = {
        "checkout.session.completed": handle_checkout_completed,
        "customer.subscription.created": handle_subscription_created,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_deleted,
        "invoice.payment_succeeded": handle_payment_succeeded,
        "invoice.payment_failed": handle_payment_failed,
    }

    handler = handlers.get(event_type)
    if handler:
        try:
            handler(data_object)
        except Exception as e:
            logger.error("Webhook error: type=%s, id=%s, error=%s", event_type, event["id"], e)
            return HttpResponse(status=500)
    else:
        logger.info("Unhandled event type: %s", event_type)

    return HttpResponse(status=200)
