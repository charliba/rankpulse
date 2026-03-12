"""Content models — Topics, clusters, and generated posts."""
from __future__ import annotations

from django.db import models


class ContentCluster(models.Model):
    """A topic cluster for content strategy (pillar + satellites)."""

    site = models.ForeignKey(
        "core.Site", on_delete=models.CASCADE, related_name="content_clusters",
    )
    name = models.CharField(max_length=200, verbose_name="Nome do Cluster")
    pillar_keyword = models.CharField(max_length=300, verbose_name="Keyword Pilar")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cluster de Conteúdo"
        verbose_name_plural = "Clusters de Conteúdo"
        ordering = ["site", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.site.name})"


class ContentTopic(models.Model):
    """A specific topic / keyword within a cluster."""

    STATUS_CHOICES = [
        ("idea", "Ideia"),
        ("planned", "Planejado"),
        ("generating", "Gerando"),
        ("review", "Em Revisão"),
        ("published", "Publicado"),
    ]

    CONTENT_TYPES = [
        ("blog_post", "Blog Post"),
        ("landing_page", "Landing Page"),
        ("faq", "FAQ"),
        ("guide", "Guia Completo"),
        ("comparison", "Comparativo"),
        ("case_study", "Case Study"),
    ]

    cluster = models.ForeignKey(
        ContentCluster, on_delete=models.CASCADE, related_name="topics",
    )
    title = models.CharField(max_length=300, verbose_name="Título")
    target_keyword = models.CharField(max_length=300, verbose_name="Keyword Alvo")
    content_type = models.CharField(
        max_length=20, choices=CONTENT_TYPES, default="blog_post",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="idea")
    search_volume = models.IntegerField(default=0, verbose_name="Volume de Busca")
    difficulty = models.IntegerField(
        default=0, verbose_name="Dificuldade (0-100)",
    )
    priority = models.IntegerField(default=0, verbose_name="Prioridade (1-10)")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tópico de Conteúdo"
        verbose_name_plural = "Tópicos de Conteúdo"
        ordering = ["-priority", "title"]

    def __str__(self) -> str:
        return f"[{self.get_status_display()}] {self.title}"


class GeneratedPost(models.Model):
    """AI-generated blog post content."""

    topic = models.ForeignKey(
        ContentTopic, on_delete=models.CASCADE, related_name="generated_posts",
    )
    title = models.CharField(max_length=300, verbose_name="Título Gerado")
    slug = models.SlugField(max_length=300, blank=True)
    meta_description = models.CharField(max_length=200, blank=True)
    content_html = models.TextField(verbose_name="Conteúdo HTML")
    content_markdown = models.TextField(blank=True, verbose_name="Conteúdo Markdown")
    word_count = models.IntegerField(default=0)

    # AI metadata
    model_used = models.CharField(max_length=50, blank=True, verbose_name="Modelo IA")
    prompt_used = models.TextField(blank=True, verbose_name="Prompt Utilizado")
    tokens_used = models.IntegerField(default=0)

    # Publishing
    is_approved = models.BooleanField(default=False, verbose_name="Aprovado")
    published_url = models.URLField(blank=True, verbose_name="URL Publicada")
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Post Gerado"
        verbose_name_plural = "Posts Gerados"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status = "✅" if self.is_approved else "⬜"
        return f"{status} {self.title}"


class SocialPost(models.Model):
    """AI-generated social media post (BestContent-style)."""

    PLATFORM_CHOICES = [
        ("instagram_feed", "Instagram Feed"),
        ("instagram_stories", "Instagram Stories"),
        ("instagram_reels", "Instagram Reels"),
        ("facebook", "Facebook"),
        ("linkedin", "LinkedIn"),
        ("tiktok", "TikTok"),
    ]

    STATUS_CHOICES = [
        ("draft", "Rascunho"),
        ("review", "Em Revisão"),
        ("approved", "Aprovado"),
        ("scheduled", "Agendado"),
        ("published", "Publicado"),
        ("rejected", "Rejeitado"),
    ]

    project = models.ForeignKey(
        "core.Project", on_delete=models.CASCADE, related_name="social_posts",
    )
    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Content
    theme = models.CharField(max_length=300, verbose_name="Tema / Assunto")
    caption = models.TextField(verbose_name="Legenda / Copy")
    hashtags = models.TextField(blank=True, verbose_name="Hashtags")
    cta = models.CharField(max_length=300, blank=True, verbose_name="Call-to-Action")

    # Visual
    image_prompt = models.TextField(blank=True, verbose_name="Prompt da Imagem")
    image_url = models.URLField(blank=True, verbose_name="URL da Imagem Gerada")
    image_file = models.ImageField(upload_to="social_images/", blank=True)

    # AI metadata
    model_used = models.CharField(max_length=80, blank=True)
    generation_params = models.JSONField(default=dict, blank=True)

    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Post Social"
        verbose_name_plural = "Posts Sociais"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.get_platform_display()}] {self.theme[:60]}"


class ContentCalendar(models.Model):
    """Weekly content plan entry — ties SocialPosts to dates."""

    project = models.ForeignKey(
        "core.Project", on_delete=models.CASCADE, related_name="calendar_entries",
    )
    post = models.ForeignKey(
        SocialPost, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="calendar_entries",
    )
    date = models.DateField()
    time_slot = models.TimeField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "Entrada Calendário"
        verbose_name_plural = "Calendário de Conteúdo"
        ordering = ["date", "time_slot"]

    def __str__(self) -> str:
        return f"{self.date} — {self.post or self.notes}"
