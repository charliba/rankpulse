"""Core models — AIProvider, ProjectLearningContext, ExpertArticle."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from .project import Project


class AIProvider(models.Model):
    """AI provider configuration per project — one API key per provider."""

    PROVIDER_CHOICES = [
        ("openai", "OpenAI"), ("google", "Google (Gemini)"),
        ("anthropic", "Anthropic (Claude)"), ("xai", "xAI (Grok)"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="ai_providers", verbose_name="Projeto")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, verbose_name="Provedor")
    api_key = models.CharField(max_length=500, verbose_name="API Key")
    text_model = models.CharField(max_length=100, blank=True, default="", verbose_name="Modelo de Texto")
    image_model = models.CharField(max_length=100, blank=True, default="", verbose_name="Modelo de Imagem")
    is_default_text = models.BooleanField(default=False, verbose_name="Padrão para Texto")
    is_default_image = models.BooleanField(default=False, verbose_name="Padrão para Imagem")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Provedor de IA"
        verbose_name_plural = "Provedores de IA"
        ordering = ["project", "-is_default_text", "provider"]
        unique_together = [("project", "provider")]

    def __str__(self) -> str:
        default = " ★" if self.is_default_text else ""
        return f"{self.get_provider_display()}{default}"

    def save(self, *args, **kwargs):
        if self.is_default_text:
            AIProvider.objects.filter(project=self.project, is_default_text=True).exclude(pk=self.pk).update(is_default_text=False)
        if self.is_default_image:
            AIProvider.objects.filter(project=self.project, is_default_image=True).exclude(pk=self.pk).update(is_default_image=False)
        super().save(*args, **kwargs)


class ProjectLearningContext(models.Model):
    """Accumulated AI context per project — the 'brain' that evolves with each user interaction."""

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="learning_context", verbose_name="Projeto")
    compiled_prompt = models.TextField(blank=True, verbose_name="Prompt Compilado", help_text="Contexto enviado à IA em cada auditoria — editável pelo usuário")
    general_guidelines = models.TextField(blank=True, verbose_name="Orientações Gerais", help_text="Regras e preferências do usuário em texto livre")
    auto_summary = models.TextField(blank=True, verbose_name="Resumo Automático", help_text="Resumo gerado pela IA a partir das observações acumuladas")
    last_compiled_at = models.DateTimeField(null=True, blank=True)
    notes_count_at_compile = models.IntegerField(default=0, verbose_name="Notas no último compile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contexto de Aprendizado"
        verbose_name_plural = "Contextos de Aprendizado"

    def __str__(self) -> str:
        return f"Learning Context — {self.project.name}"


class ExpertArticle(models.Model):
    """Expert knowledge article — embedded in ChromaDB for AI-only use."""

    CATEGORY_CHOICES = [
        ("google_ads", "Google Ads"), ("meta_ads", "Meta Ads"),
        ("seo", "SEO"), ("analytics", "Analytics / GA4"),
        ("landing_page", "Landing Pages"), ("copywriting", "Copywriting Publicitário"),
        ("conversion", "Otimização de Conversão"), ("general", "Marketing Digital Geral"),
    ]

    title = models.CharField(max_length=300, verbose_name="Título")
    source_url = models.URLField(blank=True, verbose_name="URL de Origem")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="general")
    content = models.TextField(verbose_name="Conteúdo", help_text="Texto completo do artigo / conhecimento especialista")
    chunk_count = models.IntegerField(default=0, verbose_name="Chunks Embeddados")
    embedded_at = models.DateTimeField(null=True, blank=True, verbose_name="Último Embedding")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Artigo Especialista"
        verbose_name_plural = "Artigos Especialistas"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.get_category_display()}] {self.title}"
