"""Channels admin — Channel and credential management."""
from django.contrib import admin

from .models import Channel, ChannelCredential


class ChannelCredentialInline(admin.StackedInline):
    """Inline credentials editor for a channel."""

    model = ChannelCredential
    extra = 0
    max_num = 1
    fieldsets = [
        ("Google Ads", {
            "fields": [
                "customer_id", "developer_token", "client_id",
                "client_secret", "refresh_token", "login_customer_id",
            ],
            "classes": ["collapse"],
        }),
        ("Meta Ads", {
            "fields": ["access_token", "account_id"],
            "classes": ["collapse"],
        }),
        ("Extras", {
            "fields": ["extra"],
            "classes": ["collapse"],
        }),
    ]


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    """Admin for traffic channels."""

    list_display = ["name", "project", "platform", "is_configured", "is_active"]
    list_filter = ["platform", "is_active", "project"]
    search_fields = ["name", "project__name"]
    inlines = [ChannelCredentialInline]

    @admin.display(boolean=True, description="Configurado")
    def is_configured(self, obj):
        return obj.is_configured
