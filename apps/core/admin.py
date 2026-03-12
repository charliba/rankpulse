"""Core admin — Project, Site, KPI, and Expert Knowledge management."""
from django.contrib import admin

from .models import (
    AuditConfig, AuditRecommendation, AuditReport,
    ExpertArticle, GA4EventDefinition, KPIGoal, Project,
    ProjectScore, Site, SystemErrorLog, WeeklySnapshot,
)


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


@admin.register(AuditReport)
class AuditReportAdmin(admin.ModelAdmin):
    list_display = ["id", "project", "status", "overall_score", "duration_seconds", "created_at"]
    list_filter = ["status", "project"]
    readonly_fields = ["created_at"]


@admin.register(AuditRecommendation)
class AuditRecommendationAdmin(admin.ModelAdmin):
    list_display = ["title", "report", "platform", "category", "impact", "status"]
    list_filter = ["platform", "impact", "status"]
    search_fields = ["title"]


@admin.register(AuditConfig)
class AuditConfigAdmin(admin.ModelAdmin):
    list_display = ["project", "ai_depth", "ai_language", "source_meta_ads", "source_google_ads", "source_ga4", "source_seo"]
    list_filter = ["ai_depth", "ai_language"]


@admin.register(ExpertArticle)
class ExpertArticleAdmin(admin.ModelAdmin):
    """Admin for expert knowledge articles — auto-embeds on save."""

    list_display = ["title", "category", "chunk_count", "is_active", "embedded_at", "created_at"]
    list_filter = ["category", "is_active"]
    search_fields = ["title", "content"]
    readonly_fields = ["chunk_count", "embedded_at", "created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["title", "source_url", "category", "is_active"]}),
        ("Conteúdo", {"fields": ["content"]}),
        ("Embedding", {"fields": ["chunk_count", "embedded_at", "created_at", "updated_at"]}),
    ]
    actions = ["embed_selected"]

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)
        # Auto-embed after save
        if obj.is_active:
            try:
                from .knowledge_base import embed_article
                embed_article(obj.id)
                self.message_user(request, f"✅ Artigo embeddado com {obj.chunk_count} chunks.")
            except Exception as e:
                self.message_user(request, f"⚠️ Erro ao embeddar: {e}", level="warning")

    def delete_model(self, request, obj):
        try:
            from .knowledge_base import remove_article
            remove_article(obj.id)
        except Exception:
            pass
        super().delete_model(request, obj)

    @admin.action(description="Embeddar artigos selecionados no ChromaDB")
    def embed_selected(self, request, queryset):
        from .knowledge_base import embed_article
        success, failed = 0, 0
        for article in queryset.filter(is_active=True):
            try:
                embed_article(article.id)
                success += 1
            except Exception:
                failed += 1
        self.message_user(request, f"✅ {success} embeddados, {failed} falharam.")


@admin.register(SystemErrorLog)
class SystemErrorLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "severity", "error_type", "error_message_short", "user", "view_name", "resolved"]
    list_filter = ["severity", "error_type", "resolved"]
    search_fields = ["error_message", "view_name", "url_path"]
    readonly_fields = ["timestamp"]
    list_editable = ["resolved"]

    def error_message_short(self, obj):
        return obj.error_message[:80]
    error_message_short.short_description = "Mensagem"


@admin.register(ProjectScore)
class ProjectScoreAdmin(admin.ModelAdmin):
    list_display = ["project", "overall_score", "audit_score", "earned_points", "pending_points", "total_possible"]
    readonly_fields = ["last_calculated_at", "created_at", "updated_at"]
