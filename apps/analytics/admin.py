"""Analytics admin configuration."""
from django.contrib import admin

from .models import GA4EventLog, GA4Report, SearchConsoleData


@admin.register(GA4EventLog)
class GA4EventLogAdmin(admin.ModelAdmin):
    """Admin for GA4 event logs."""

    list_display = ["event_name", "site", "client_id", "status", "response_code", "created_at"]
    list_filter = ["site", "status", "event_name"]
    search_fields = ["event_name", "client_id"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"


@admin.register(SearchConsoleData)
class SearchConsoleDataAdmin(admin.ModelAdmin):
    """Admin for GSC data."""

    list_display = ["date", "site", "query_short", "page_short", "clicks", "impressions", "ctr", "position"]
    list_filter = ["site", "device", "country"]
    search_fields = ["query", "page"]
    date_hierarchy = "date"

    @admin.display(description="Query")
    def query_short(self, obj: SearchConsoleData) -> str:
        return obj.query[:60] + "..." if len(obj.query) > 60 else obj.query

    @admin.display(description="Page")
    def page_short(self, obj: SearchConsoleData) -> str:
        return obj.page.replace("https://beezle.io", "") or "/"


@admin.register(GA4Report)
class GA4ReportAdmin(admin.ModelAdmin):
    """Admin for GA4 aggregated reports."""

    list_display = ["report_type", "site", "date_start", "date_end", "created_at"]
    list_filter = ["site", "report_type"]
    date_hierarchy = "date_end"
