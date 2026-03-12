from django.contrib import admin
from .models import Subscription, PaymentHistory


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "billing_interval", "current_period_end", "updated_at")
    list_filter = ("status", "plan", "billing_interval")
    search_fields = ("user__username", "user__email", "stripe_customer_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ("subscription", "amount_display", "status", "payment_method", "created_at")
    list_filter = ("status",)
    readonly_fields = ("id", "created_at")

    def amount_display(self, obj):
        return f"R$ {obj.amount_cents / 100:.2f}"
    amount_display.short_description = "Valor"
