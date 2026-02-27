"""Core app configuration."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Core application — site management, dashboard, base models."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"
