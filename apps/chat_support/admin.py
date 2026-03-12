"""Admin do chat de suporte Aura."""
from django.contrib import admin

from .models import ChatMessage, ChatSession, ChatSettings, FeedbackLog


class ChatMessageInline(admin.TabularInline):
    """Inline de mensagens na sessão."""

    model = ChatMessage
    extra = 0
    readonly_fields = ("id", "sender", "content", "created_at")
    ordering = ("created_at",)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """Admin de sessões de chat."""

    list_display = ("id", "user", "status", "started_at")
    list_filter = ("status", "started_at")
    search_fields = ("user__username", "visitor_id")
    readonly_fields = ("id", "started_at")
    inlines = (ChatMessageInline,)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin de mensagens."""

    list_display = ("short_content", "sender", "session", "created_at")
    list_filter = ("sender", "created_at")

    @admin.display(description="Conteúdo")
    def short_content(self, obj: ChatMessage) -> str:
        return obj.content[:80]


@admin.register(ChatSettings)
class ChatSettingsAdmin(admin.ModelAdmin):
    """Admin singleton de configurações."""

    list_display = ("__str__", "ai_enabled", "updated_at")

    def has_add_permission(self, request) -> bool:
        return not ChatSettings.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(FeedbackLog)
class FeedbackLogAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "priority", "status", "user", "created_at")
    list_filter = ("category", "status", "priority", "created_at")
    search_fields = ("title", "description", "user__username")
    readonly_fields = ("created_at", "updated_at", "chat_transcript", "user_agent", "error_context")
