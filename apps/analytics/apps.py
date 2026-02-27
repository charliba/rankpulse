"""Analytics app configuration."""
from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Analytics — GA4 Measurement Protocol, Search Console API, reporting."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    verbose_name = "Analytics"
