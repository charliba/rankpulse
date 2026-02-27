"""Content admin configuration."""
from django.contrib import admin

from .models import ContentCluster, ContentTopic, GeneratedPost


class ContentTopicInline(admin.TabularInline):
    model = ContentTopic
    extra = 1
    fields = ("title", "target_keyword", "content_type", "status", "priority")


@admin.register(ContentCluster)
class ContentClusterAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "pillar_keyword", "is_active", "created_at")
    list_filter = ("site", "is_active")
    inlines = [ContentTopicInline]


@admin.register(ContentTopic)
class ContentTopicAdmin(admin.ModelAdmin):
    list_display = ("title", "cluster", "target_keyword", "content_type", "status", "priority")
    list_filter = ("status", "content_type", "cluster__site")
    search_fields = ("title", "target_keyword")


@admin.register(GeneratedPost)
class GeneratedPostAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "model_used", "word_count", "is_approved", "created_at")
    list_filter = ("is_approved", "model_used", "topic__cluster__site")
    search_fields = ("title",)
    readonly_fields = ("tokens_used", "word_count", "created_at", "updated_at")
