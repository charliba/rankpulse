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


# ── Social Content (HTML views) ────────────────────────────────

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages as dj_messages

from apps.core.models import Project

from .models import SocialPost


def _get_user_project(request, project_id):
    if request.user.is_superuser:
        return get_object_or_404(Project, pk=project_id)
    return get_object_or_404(Project, pk=project_id, owner=request.user)


def _base_context(request):
    return {"projects": Project.objects.filter(owner=request.user, is_active=True)}


@login_required
def social_dashboard(request, project_id):
    """Social content hub — list posts, generate, manage queue."""
    project = _get_user_project(request, project_id)
    posts_qs = SocialPost.objects.filter(project=project)
    status_filter = request.GET.get("status", "")
    if status_filter:
        posts_qs = posts_qs.filter(status=status_filter)

    # Fetch content-related audit recommendations for integration
    from apps.core.models import AuditRecommendation
    content_categories = ("ad_copy", "creative", "content_gap")
    audit_recs = AuditRecommendation.objects.filter(
        report__project=project,
        category__in=content_categories,
        status="pending",
    ).select_related("report").order_by("-report__created_at", "impact")[:10]

    return render(request, "content/social_dashboard.html", {
        **_base_context(request),
        "page_title": f"Social Content — {project.name}",
        "page_id": "social_content",
        "project": project,
        "posts": posts_qs[:100],
        "status_filter": status_filter,
        "status_choices": SocialPost.STATUS_CHOICES,
        "platform_choices": SocialPost.PLATFORM_CHOICES,
        "audit_recs": audit_recs,
    })


@login_required
def social_generate(request, project_id):
    """POST: generate social posts from themes."""
    project = _get_user_project(request, project_id)

    if request.method == "POST":
        from .social_generator import SocialContentGenerator
        gen = SocialContentGenerator(project)

        action = request.POST.get("action", "post")

        if action == "themes":
            platform = request.POST.get("platform", "instagram_feed")
            count = int(request.POST.get("count", "5"))
            count = min(count, 20)
            themes = gen.generate_themes(count=count, platforms=[platform])
            return JsonResponse({"themes": themes})

        elif action == "post":
            theme = request.POST.get("theme", "").strip()
            platform = request.POST.get("platform", "instagram_feed")
            style = request.POST.get("style", "")
            if not theme:
                return JsonResponse({"error": "Tema é obrigatório"}, status=400)
            post = gen.generate_post(theme=theme, platform=platform, style=style)
            if post:
                return JsonResponse({
                    "success": True,
                    "post_id": post.pk,
                    "caption": post.caption,
                    "hashtags": post.hashtags,
                    "cta": post.cta,
                    "image_prompt": post.image_prompt,
                })
            return JsonResponse({"error": "Falha na geração"}, status=500)

        elif action == "batch":
            themes_raw = request.POST.get("themes", "")
            platform = request.POST.get("platform", "instagram_feed")
            themes = [t.strip() for t in themes_raw.split("\n") if t.strip()]
            if not themes:
                return JsonResponse({"error": "Nenhum tema informado"}, status=400)
            posts = gen.generate_batch(themes=themes[:10], platform=platform)
            return JsonResponse({
                "success": True,
                "count": len(posts),
                "post_ids": [p.pk for p in posts],
            })

    return JsonResponse({"error": "POST required"}, status=405)


@login_required
def social_post_detail(request, project_id, post_id):
    """View/edit a single social post."""
    project = _get_user_project(request, project_id)
    post = get_object_or_404(SocialPost, pk=post_id, project=project)

    if request.method == "POST":
        action = request.POST.get("action", "save")

        if action == "save":
            post.caption = request.POST.get("caption", post.caption)
            post.hashtags = request.POST.get("hashtags", post.hashtags)
            post.cta = request.POST.get("cta", post.cta)
            post.status = request.POST.get("status", post.status)
            post.save()
            dj_messages.success(request, "Post atualizado!")

        elif action == "generate_image":
            from .social_generator import SocialContentGenerator
            gen = SocialContentGenerator(project)
            url = gen.generate_image(post)
            if url:
                dj_messages.success(request, "Imagem gerada!")
            else:
                dj_messages.error(request, "Falha ao gerar imagem.")

        elif action == "delete":
            post.delete()
            dj_messages.success(request, "Post removido!")
            return redirect("content:social_dashboard", project_id=project.pk)

        return redirect("content:social_post_detail",
                        project_id=project.pk, post_id=post.pk)

    return render(request, "content/social_post_detail.html", {
        **_base_context(request),
        "page_title": f"Post — {post.theme[:50]}",
        "page_id": "social_content",
        "project": project,
        "post": post,
    })
