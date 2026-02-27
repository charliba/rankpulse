"""Content views — API endpoints for content generation."""
from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import Site

from .generator import ContentGenerator
from .models import ContentCluster, ContentTopic, GeneratedPost


@require_POST
def generate(request, site_id: int) -> JsonResponse:
    """Generate content for a topic.

    POST /api/content/<site_id>/generate/
    Body: {"topic_id": 1} or {"title": "...", "keyword": "..."}
    """
    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    topic_id = body.get("topic_id")

    if topic_id:
        try:
            topic = ContentTopic.objects.get(pk=topic_id, cluster__site=site)
        except ContentTopic.DoesNotExist:
            return JsonResponse({"error": "Topic not found"}, status=404)
        title = topic.title
        keyword = topic.target_keyword
        content_type = topic.content_type
    else:
        title = body.get("title", "")
        keyword = body.get("keyword", "")
        content_type = body.get("content_type", "blog_post")
        topic = None

    if not title or not keyword:
        return JsonResponse({"error": "title and keyword are required"}, status=400)

    generator = ContentGenerator()
    result = generator.generate_post(
        topic_title=title,
        target_keyword=keyword,
        site_name=site.name,
        site_domain=site.domain,
        content_type=content_type,
    )

    # Save if linked to a topic
    if topic:
        post = GeneratedPost.objects.create(
            topic=topic,
            title=result["title"],
            slug=result["slug"],
            meta_description=result["meta_description"],
            content_html=result["content_html"],
            content_markdown=result.get("content_markdown", ""),
            word_count=result["word_count"],
            model_used=result["model_used"],
            prompt_used=result["prompt_used"],
            tokens_used=result["tokens_used"],
        )
        topic.status = "review"
        topic.save(update_fields=["status"])
        result["post_id"] = post.pk

    return JsonResponse(result)


@require_GET
def topics(request, site_id: int) -> JsonResponse:
    """List content topics for a site.

    GET /api/content/<site_id>/topics/?status=idea
    """
    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    qs = ContentTopic.objects.filter(cluster__site=site).select_related("cluster")
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    data = [
        {
            "id": t.pk,
            "title": t.title,
            "keyword": t.target_keyword,
            "cluster": t.cluster.name,
            "content_type": t.content_type,
            "status": t.status,
            "priority": t.priority,
        }
        for t in qs[:100]
    ]
    return JsonResponse({"topics": data, "count": len(data)})


@require_GET
def posts(request, site_id: int) -> JsonResponse:
    """List generated posts for a site.

    GET /api/content/<site_id>/posts/?approved_only=true
    """
    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    qs = GeneratedPost.objects.filter(topic__cluster__site=site)
    if request.GET.get("approved_only", "").lower() in ("true", "1"):
        qs = qs.filter(is_approved=True)

    data = [
        {
            "id": p.pk,
            "title": p.title,
            "slug": p.slug,
            "word_count": p.word_count,
            "is_approved": p.is_approved,
            "published_url": p.published_url,
            "created_at": p.created_at.isoformat(),
        }
        for p in qs[:50]
    ]
    return JsonResponse({"posts": data, "count": len(data)})
