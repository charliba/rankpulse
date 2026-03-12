"""Context processors for core app."""

from django.conf import settings


def app_domain(request):
    """Expose APP_DOMAIN to all templates."""
    return {"APP_DOMAIN": getattr(settings, "APP_DOMAIN", "rankpulse.cloud")}


def error_count(request):
    """Add unresolved error count for staff users (used in sidebar badge)."""
    if hasattr(request, "user") and request.user.is_authenticated and request.user.is_staff:
        from apps.core.models import SystemErrorLog
        return {
            "unresolved_error_count": SystemErrorLog.objects.filter(resolved=False).count()
        }
    return {}
