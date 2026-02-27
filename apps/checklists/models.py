"""Checklists models — Templates and checklist instances."""
from __future__ import annotations

from django.db import models


class ChecklistTemplate(models.Model):
    """Reusable checklist template (weekly, monthly, etc.)."""

    FREQUENCY_CHOICES = [
        ("weekly", "Semanal"),
        ("biweekly", "Quinzenal"),
        ("monthly", "Mensal"),
        ("quarterly", "Trimestral"),
        ("one_time", "Única Vez"),
    ]

    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="weekly")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Template de Checklist"
        verbose_name_plural = "Templates de Checklists"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_frequency_display()})"


class ChecklistTemplateItem(models.Model):
    """An item within a checklist template."""

    CATEGORY_CHOICES = [
        ("analytics", "Analytics"),
        ("seo", "SEO"),
        ("content", "Conteúdo"),
        ("technical", "Técnico"),
        ("social", "Social Media"),
        ("reporting", "Relatórios"),
    ]

    template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.CASCADE, related_name="items",
    )
    title = models.CharField(max_length=300, verbose_name="Título")
    description = models.TextField(blank=True, verbose_name="Descrição / Instrução")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="seo")
    order = models.IntegerField(default=0, verbose_name="Ordem")
    tool_hint = models.CharField(
        max_length=200, blank=True, verbose_name="Ferramenta",
        help_text="Ex: GA4, GSC, Ahrefs, RankPulse",
    )

    class Meta:
        verbose_name = "Item do Template"
        verbose_name_plural = "Items do Template"
        ordering = ["order", "title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.template.name})"


class ChecklistInstance(models.Model):
    """A concrete checklist for a specific site and period."""

    site = models.ForeignKey(
        "core.Site", on_delete=models.CASCADE, related_name="checklists",
    )
    template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.CASCADE, related_name="instances",
    )
    period_start = models.DateField(verbose_name="Início do Período")
    period_end = models.DateField(verbose_name="Fim do Período")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Checklist"
        verbose_name_plural = "Checklists"
        ordering = ["-period_start"]

    def __str__(self) -> str:
        return f"{self.template.name} — {self.site.name} ({self.period_start})"

    @property
    def progress(self) -> int:
        """Calculate completion percentage."""
        total = self.completed_items.count()
        done = self.completed_items.filter(is_done=True).count()
        return int(done / total * 100) if total else 0


class ChecklistCompletedItem(models.Model):
    """Tracking which items have been completed in a checklist instance."""

    instance = models.ForeignKey(
        ChecklistInstance, on_delete=models.CASCADE, related_name="completed_items",
    )
    template_item = models.ForeignKey(
        ChecklistTemplateItem, on_delete=models.CASCADE,
    )
    is_done = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Item Completado"
        verbose_name_plural = "Items Completados"
        unique_together = ["instance", "template_item"]

    def __str__(self) -> str:
        status = "✅" if self.is_done else "⬜"
        return f"{status} {self.template_item.title}"
