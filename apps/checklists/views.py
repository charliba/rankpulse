"""Checklists views — API endpoints for checklist management."""
from __future__ import annotations

import json

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import Site

from .models import (
    ChecklistCompletedItem,
    ChecklistInstance,
    ChecklistTemplate,
    ChecklistTemplateItem,
)


@require_POST
def create_checklist(request, site_id: int) -> JsonResponse:
    """Create a new checklist instance from a template.

    POST /api/checklists/<site_id>/create/
    Body: {"template_id": 1, "period_start": "2026-02-24", "period_end": "2026-03-02"}
    """
    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    template_id = body.get("template_id")
    if not template_id:
        return JsonResponse({"error": "template_id is required"}, status=400)

    try:
        template = ChecklistTemplate.objects.get(pk=template_id, is_active=True)
    except ChecklistTemplate.DoesNotExist:
        return JsonResponse({"error": "Template not found"}, status=404)

    from datetime import date
    today = date.today()
    period_start = body.get("period_start", today.isoformat())
    period_end = body.get("period_end", (today + timezone.timedelta(days=6)).isoformat())

    instance = ChecklistInstance.objects.create(
        site=site,
        template=template,
        period_start=period_start,
        period_end=period_end,
    )

    # Create items from template
    for item in template.items.all():
        ChecklistCompletedItem.objects.create(
            instance=instance,
            template_item=item,
        )

    return JsonResponse({
        "checklist_id": instance.pk,
        "template": template.name,
        "items_count": instance.completed_items.count(),
    })


@require_POST
def toggle_item(request, site_id: int) -> JsonResponse:
    """Toggle a checklist item.

    POST /api/checklists/<site_id>/toggle/
    Body: {"item_id": 1}
    """
    body = json.loads(request.body)
    item_id = body.get("item_id")

    try:
        item = ChecklistCompletedItem.objects.select_related(
            "instance__site",
        ).get(pk=item_id, instance__site_id=site_id)
    except ChecklistCompletedItem.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

    item.is_done = not item.is_done
    item.completed_at = timezone.now() if item.is_done else None
    item.save(update_fields=["is_done", "completed_at"])

    return JsonResponse({
        "item_id": item.pk,
        "is_done": item.is_done,
        "progress": item.instance.progress,
    })


@require_GET
def checklist_detail(request, site_id: int, checklist_id: int) -> JsonResponse:
    """Get a checklist with all items.

    GET /api/checklists/<site_id>/<checklist_id>/
    """
    try:
        instance = ChecklistInstance.objects.select_related(
            "template", "site",
        ).get(pk=checklist_id, site_id=site_id)
    except ChecklistInstance.DoesNotExist:
        return JsonResponse({"error": "Checklist not found"}, status=404)

    items = instance.completed_items.select_related("template_item").all()

    return JsonResponse({
        "id": instance.pk,
        "template": instance.template.name,
        "site": instance.site.name,
        "period_start": instance.period_start.isoformat(),
        "period_end": instance.period_end.isoformat(),
        "progress": instance.progress,
        "items": [
            {
                "id": item.pk,
                "title": item.template_item.title,
                "category": item.template_item.category,
                "is_done": item.is_done,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "notes": item.notes,
            }
            for item in items
        ],
    })


@require_GET
def list_checklists(request, site_id: int) -> JsonResponse:
    """List all checklists for a site.

    GET /api/checklists/<site_id>/
    """
    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    instances = ChecklistInstance.objects.filter(site=site).select_related("template")[:20]

    data = [
        {
            "id": i.pk,
            "template": i.template.name,
            "period_start": i.period_start.isoformat(),
            "period_end": i.period_end.isoformat(),
            "progress": i.progress,
        }
        for i in instances
    ]
    return JsonResponse({"checklists": data, "count": len(data)})
