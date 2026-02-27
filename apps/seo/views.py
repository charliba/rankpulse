"""SEO views — API endpoints for SEO auditing."""
from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import Site

from .auditor import SEOAuditor
from .models import KeywordTracking, SEOAudit


@require_POST
def run_audit(request, site_id: int) -> JsonResponse:
    """Start an SEO audit for a site.

    POST /api/seo/<site_id>/audit/
    """
    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    auditor = SEOAuditor(site)
    audit = auditor.run()

    return JsonResponse({
        "audit_id": audit.pk,
        "status": audit.status,
        "overall_score": audit.overall_score,
        "pages_crawled": audit.pages_crawled,
        "issues_critical": audit.issues_critical,
        "issues_warning": audit.issues_warning,
        "recommendations": audit.recommendations,
    })


@require_GET
def audit_history(request, site_id: int) -> JsonResponse:
    """Get audit history for a site.

    GET /api/seo/<site_id>/audits/?limit=10
    """
    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    limit = min(int(request.GET.get("limit", 10)), 50)
    audits = SEOAudit.objects.filter(site=site)[:limit]

    data = [
        {
            "id": a.pk,
            "status": a.status,
            "overall_score": a.overall_score,
            "pages_crawled": a.pages_crawled,
            "issues_critical": a.issues_critical,
            "issues_warning": a.issues_warning,
            "created_at": a.created_at.isoformat(),
        }
        for a in audits
    ]
    return JsonResponse({"audits": data})


@require_GET
def keywords(request, site_id: int) -> JsonResponse:
    """Get tracked keywords for a site.

    GET /api/seo/<site_id>/keywords/?priority_only=true
    """
    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    qs = KeywordTracking.objects.filter(site=site)
    if request.GET.get("priority_only", "").lower() in ("true", "1"):
        qs = qs.filter(is_priority=True)

    data = [
        {
            "keyword": kw.keyword,
            "position": float(kw.current_position),
            "best_position": float(kw.best_position),
            "clicks_30d": kw.clicks_30d,
            "impressions_30d": kw.impressions_30d,
            "is_priority": kw.is_priority,
        }
        for kw in qs[:100]
    ]
    return JsonResponse({"keywords": data, "count": len(data)})
