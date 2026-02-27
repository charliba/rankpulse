"""
Modelos do chat de suporte Aura — IA assistente do RankPulse.

Três modelos:
  - ChatSession: sessão persistente por usuário
  - ChatMessage: mensagem individual (user / ai / system)
  - ChatSettings: singleton com configurações globais
"""
import uuid

from django.conf import settings as django_settings
from django.db import models


class ChatSession(models.Model):
    """Sessão de chat de um usuário com a Aura."""

    STATUS_CHOICES = [
        ("active", "Ativa"),
        ("closed", "Encerrada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_sessions",
    )
    visitor_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Sessão de Chat"
        verbose_name_plural = "Sessões de Chat"

    def __str__(self) -> str:
        if self.user:
            return f"Chat {self.id} — {self.user.username}"
        return f"Chat {self.id} — Visitante {self.visitor_id[:8]}"


class ChatMessage(models.Model):
    """Mensagem individual no chat."""

    SENDER_CHOICES = [
        ("user", "Usuário"),
        ("ai", "Aura (IA)"),
        ("system", "Sistema"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"

    def __str__(self) -> str:
        return f"{self.sender}: {self.content[:50]}"


class ChatSettings(models.Model):
    """Configurações globais do chat (singleton — pk=1)."""

    ai_enabled = models.BooleanField(default=True, verbose_name="IA Habilitada")
    welcome_message = models.TextField(
        default=(
            "Olá! ✨ Eu sou a **Aura**, assistente virtual do RankPulse. "
            "Posso te ajudar a configurar seu site, entender métricas GA4, "
            "Search Console, KPIs e muito mais. Como posso ajudar?"
        ),
        verbose_name="Mensagem de Boas-vindas",
    )
    ai_system_prompt = models.TextField(
        default="",
        verbose_name="Prompt do Sistema (backup)",
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração do Chat"
        verbose_name_plural = "Configurações do Chat"

    def __str__(self) -> str:
        return "Configurações Aura"

    @classmethod
    def get_settings(cls) -> "ChatSettings":
        """Retorna o registro singleton, criando se necessário."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
