"""Core models — Project and ProjectScore."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Project(models.Model):
    """A project/business managed in RankPulse (e.g. 'My Face', 'Beezle')."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="Proprietário",
    )
    name = models.CharField(max_length=200, verbose_name="Nome do Projeto")
    slug = models.SlugField(max_length=220, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Descrição")
    business_goals = models.TextField(
        blank=True, verbose_name="Objetivos do Negócio",
        help_text="Ex: Gerar leads, vendas online, brand awareness, agendamentos",
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        unique_together = ["owner", "slug"]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProjectScore(models.Model):
    """Unified gamification score — combines audit score and recommendation points."""

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="score",
        verbose_name="Projeto",
    )
    overall_score = models.IntegerField(default=0, verbose_name="Score Geral (0-100)")
    audit_score = models.IntegerField(default=0, verbose_name="Score Auditoria")
    pending_points = models.IntegerField(default=0, verbose_name="Pontos Pendentes")
    earned_points = models.IntegerField(default=0, verbose_name="Pontos Conquistados")
    total_possible = models.IntegerField(default=0, verbose_name="Total Possível")
    last_calculated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Score do Projeto"
        verbose_name_plural = "Scores dos Projetos"

    def __str__(self) -> str:
        return f"Score {self.overall_score}/100 — {self.project.name}"
