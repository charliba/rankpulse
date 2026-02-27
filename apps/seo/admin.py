"""SEO admin configuration."""
from django.contrib import admin

from .models import KeywordTracking, PageScore, SEOAudit


class PageScoreInline(admin.TabularInline):
    model = PageScore
    extra = 0
    readonly_fields = ("url", "score", "http_status", "load_time_ms")
    fields = ("url", "score", "has_title", "has_meta_description", "has_h1", "has_structured_data", "http_status")


@admin.register(SEOAudit)
class SEOAuditAdmin(admin.ModelAdmin):
    list_display = ("site", "overall_score", "status", "pages_crawled", "issues_critical", "created_at")
    list_filter = ("status", "site")
    readonly_fields = ("started_at", "completed_at", "created_at")
    inlines = [PageScoreInline]


@admin.register(PageScore)
class PageScoreAdmin(admin.ModelAdmin):
    list_display = ("url", "score", "has_title", "has_meta_description", "has_h1", "http_status")
    list_filter = ("audit__site", "has_title", "has_meta_description", "has_h1")
    search_fields = ("url",)


@admin.register(KeywordTracking)
class KeywordTrackingAdmin(admin.ModelAdmin):
    list_display = ("keyword", "site", "current_position", "best_position", "clicks_30d", "is_priority")
    list_filter = ("site", "is_priority")
    search_fields = ("keyword",)
