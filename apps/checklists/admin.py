"""Checklists admin configuration."""
from django.contrib import admin

from .models import (
    ChecklistCompletedItem,
    ChecklistInstance,
    ChecklistTemplate,
    ChecklistTemplateItem,
)


class ChecklistTemplateItemInline(admin.TabularInline):
    model = ChecklistTemplateItem
    extra = 3
    fields = ("title", "category", "tool_hint", "order")


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "frequency", "is_active", "created_at")
    list_filter = ("frequency", "is_active")
    inlines = [ChecklistTemplateItemInline]


class ChecklistCompletedItemInline(admin.TabularInline):
    model = ChecklistCompletedItem
    extra = 0
    fields = ("template_item", "is_done", "completed_at", "notes")
    readonly_fields = ("completed_at",)


@admin.register(ChecklistInstance)
class ChecklistInstanceAdmin(admin.ModelAdmin):
    list_display = ("template", "site", "period_start", "period_end", "progress")
    list_filter = ("site", "template")
    inlines = [ChecklistCompletedItemInline]

    def progress(self, obj: ChecklistInstance) -> str:
        return f"{obj.progress}%"
    progress.short_description = "Progresso"
