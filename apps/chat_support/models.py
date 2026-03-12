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


class FeedbackLog(models.Model):
    """User feedback & bug reports submitted via Aura widget."""

    CATEGORY_CHOICES = [
        ("bug", "Bug"),
        ("feature", "Sugestão"),
        ("ux", "Usabilidade"),
        ("performance", "Performance"),
        ("other", "Outro"),
    ]
    STATUS_CHOICES = [
        ("new", "Novo"),
        ("approved", "Aprovado"),
        ("in_progress", "Em Análise"),
        ("resolved", "Resolvido"),
        ("rejected", "Rejeitado"),
        ("closed", "Fechado"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Baixa"),
        ("medium", "Média"),
        ("high", "Alta"),
        ("critical", "Crítica"),
    ]

    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback_logs",
    )
    chat_session = models.ForeignKey(
        ChatSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback_logs",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="bug")
    email = models.EmailField(max_length=254, blank=True, help_text="E-mail do remetente (útil para anônimos)")
    title = models.CharField(max_length=300)
    description = models.TextField()
    page_url = models.URLField(max_length=500, blank=True)
    screenshot = models.ImageField(upload_to="feedback/%Y/%m/", blank=True)
    chat_transcript = models.TextField(blank=True, help_text="Últimas mensagens do chat ao reportar")
    user_agent = models.CharField(max_length=500, blank=True)
    error_context = models.JSONField(default=dict, blank=True, help_text="Contexto extra do erro (URL, traceback, etc.)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    developer_notes = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True, verbose_name="Solução Aplicada")
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="Arquivado em")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Feedback"
        verbose_name_plural = "Feedbacks"

    def __str__(self) -> str:
        return f"[{self.get_category_display()}] {self.title}"


class FeedbackImage(models.Model):
    """Image attachment for a FeedbackLog entry (supports multiple images)."""

    feedback = models.ForeignKey(
        FeedbackLog,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="feedback/%Y/%m/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Imagem de Feedback"
        verbose_name_plural = "Imagens de Feedback"

    def __str__(self) -> str:
        return f"Image for Feedback #{self.feedback_id}"
