"""Core admin — Project, Site, and KPI management."""
from django.contrib import admin

from .models import GA4EventDefinition, KPIGoal, Project, Site, WeeklySnapshot


class SiteInline(admin.TabularInline):
    """Inline for sites inside a project."""

    model = Site
    extra = 0
    fields = ["name", "domain", "url", "is_active"]
    show_change_link = True


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin for projects."""

    list_display = ["name", "owner", "slug", "is_active", "created_at"]
    list_filter = ["is_active", "owner"]
    search_fields = ["name", "owner__username"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SiteInline]
    fieldsets = [
        (None, {"fields": ["owner", "name", "slug", "description", "is_active"]}),
    ]


class GA4EventDefinitionInline(admin.TabularInline):
    """Inline for GA4 event definitions."""

    model = GA4EventDefinition
    extra = 0
    fields = [
        "event_name", "priority", "is_conversion",
        "server_side", "is_implemented", "trigger_page",
    ]


class KPIGoalInline(admin.TabularInline):
    """Inline for KPI goals."""

    model = KPIGoal
    extra = 0
    fields = ["metric_name", "source", "period", "target_value", "current_value", "unit"]


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    """Admin for managed sites."""

    list_display = ["name", "project", "domain", "ga4_measurement_id", "gsc_verified", "is_active"]
    list_filter = ["is_active", "gsc_verified", "project"]
    search_fields = ["name", "domain", "project__name"]
    inlines = [GA4EventDefinitionInline, KPIGoalInline]
    fieldsets = [
        ("Geral", {"fields": ["project", "name", "domain", "url", "description", "is_active"]}),
        ("Google Analytics 4", {
            "fields": ["ga4_measurement_id", "ga4_api_secret", "ga4_property_id"],
        }),
        ("Google Search Console", {
            "fields": ["gsc_verified", "gsc_site_url"],
        }),
        ("SEO", {"fields": ["sitemap_url", "robots_txt_url"]}),
    ]


@admin.register(GA4EventDefinition)
class GA4EventDefinitionAdmin(admin.ModelAdmin):
    """Admin for GA4 event definitions."""

    list_display = [
        "event_name", "site", "priority", "is_conversion",
        "server_side", "is_implemented",
    ]
    list_filter = ["site", "priority", "is_conversion", "is_implemented", "server_side"]
    search_fields = ["event_name", "description"]
    list_editable = ["is_implemented"]


@admin.register(KPIGoal)
class KPIGoalAdmin(admin.ModelAdmin):
    """Admin for KPI goals."""

    list_display = ["metric_name", "site", "period", "target_value", "current_value", "unit"]
    list_filter = ["site", "period", "source"]
    list_editable = ["current_value"]


@admin.register(WeeklySnapshot)
class WeeklySnapshotAdmin(admin.ModelAdmin):
    """Admin for weekly snapshots."""

    list_display = [
        "site", "week_start", "organic_sessions", "gsc_clicks",
        "gsc_impressions", "signups", "posts_published",
    ]
    list_filter = ["site"]
    date_hierarchy = "week_start"
    readonly_fields = ["created_at"]
