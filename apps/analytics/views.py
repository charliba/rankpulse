"""Analytics views — API endpoints for analytics data."""
from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import Site

from .ga4_client import GA4Client
from .models import GA4EventLog


@require_POST
def send_event(request, site_id: int) -> JsonResponse:
    """Send a GA4 event via Measurement Protocol.

    POST /api/analytics/<site_id>/send-event/
    Body: {"event_name": "...", "client_id": "...", "params": {...}}
    """
    import json

    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    if not site.ga4_measurement_id or not site.ga4_api_secret:
        return JsonResponse(
            {"error": "GA4 credentials not configured for this site"}, status=400,
        )

    body = json.loads(request.body)
    event_name = body.get("event_name", "")
    client_id = body.get("client_id", "")
    params = body.get("params", {})
    debug = body.get("debug", False)

    if not event_name:
        return JsonResponse({"error": "event_name is required"}, status=400)

    client = GA4Client(
        measurement_id=site.ga4_measurement_id,
        api_secret=site.ga4_api_secret,
    )
    result = client.send_event(
        event_name=event_name,
        client_id=client_id or None,
        params=params,
        debug=debug,
    )

    # Log the event
    GA4EventLog.objects.create(
        site=site,
        event_name=event_name,
        client_id=client_id or "auto",
        parameters=params,
        status="validated" if result.get("success") else "failed",
        response_code=result.get("status_code"),
        response_body=result.get("body", ""),
    )

    return JsonResponse(result)


@require_GET
def event_logs(request, site_id: int) -> JsonResponse:
    """Get recent GA4 event logs for a site.

    GET /api/analytics/<site_id>/event-logs/?limit=50
    """
    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    limit = min(int(request.GET.get("limit", 50)), 500)
    logs = GA4EventLog.objects.filter(site=site)[:limit]

    data = [
        {
            "id": log.id,
            "event_name": log.event_name,
            "client_id": log.client_id,
            "status": log.status,
            "parameters": log.parameters,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
    return JsonResponse({"logs": data, "count": len(data)})


@require_GET
def gsc_summary(request, site_id: int) -> JsonResponse:
    """Get Search Console summary data.

    GET /api/analytics/<site_id>/gsc-summary/?days=7
    """
    from django.db.models import Avg, Sum

    from .models import SearchConsoleData

    try:
        site = Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return JsonResponse({"error": "Site not found"}, status=404)

    days = int(request.GET.get("days", 7))
    from datetime import date, timedelta
    start_date = date.today() - timedelta(days=days)

    qs = SearchConsoleData.objects.filter(site=site, date__gte=start_date)
    summary = qs.aggregate(
        total_clicks=Sum("clicks"),
        total_impressions=Sum("impressions"),
        avg_ctr=Avg("ctr"),
        avg_position=Avg("position"),
    )

    top_queries = (
        qs.values("query")
        .annotate(total_clicks=Sum("clicks"), total_impressions=Sum("impressions"))
        .order_by("-total_clicks")[:20]
    )

    return JsonResponse({
        "period_days": days,
        "summary": {
            "clicks": summary["total_clicks"] or 0,
            "impressions": summary["total_impressions"] or 0,
            "ctr": float(summary["avg_ctr"] or 0),
            "position": float(summary["avg_position"] or 0),
        },
        "top_queries": list(top_queries),
    })
