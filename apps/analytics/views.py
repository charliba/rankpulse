"""Analytics views â€” API endpoints for GA4, GSC, GA4 Admin, and Google Ads."""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import Site

from .ga4_client import GA4Client
from .models import GA4EventLog

logger = logging.getLogger(__name__)


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_site(site_id: int) -> Site | None:
    """Get an active site or None."""
    try:
        return Site.objects.get(pk=site_id, is_active=True)
    except Site.DoesNotExist:
        return None


def _get_gsc_client(site: Site):
    """Build a SearchConsoleClient for a site."""
    from .search_console import SearchConsoleClient

    key_path = getattr(settings, "GSC_SERVICE_ACCOUNT_KEY_PATH", "")
    site_url = site.gsc_site_url or site.url
    return SearchConsoleClient(service_account_key_path=key_path, site_url=site_url)


def _get_ga4_admin_client(site: Site):
    """Build a GA4AdminClient for a site."""
    from .ga4_admin import GA4AdminClient

    key_path = getattr(settings, "GA4_SERVICE_ACCOUNT_KEY_PATH", "")
    property_id = site.ga4_property_id or getattr(settings, "GA4_PROPERTY_ID", "")
    return GA4AdminClient(property_id=property_id, service_account_key_path=key_path)


def _get_ga4_report_client(site: Site):
    """Build a GA4ReportClient for a site."""
    from .ga4_report import GA4ReportClient

    key_path = getattr(settings, "GA4_SERVICE_ACCOUNT_KEY_PATH", "")
    property_id = site.ga4_property_id or getattr(settings, "GA4_PROPERTY_ID", "")
    return GA4ReportClient(property_id=property_id, service_account_key_path=key_path)


# â”€â”€ GA4 Measurement Protocol â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@require_POST
def send_event(request, site_id: int) -> JsonResponse:
    """Send a GA4 event via Measurement Protocol.

    POST /api/analytics/<site_id>/send-event/
    Body: {"event_name": "...", "client_id": "...", "params": {...}}
    """
    site = _get_site(site_id)
    if not site:
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
    site = _get_site(site_id)
    if not site:
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

    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    days = int(request.GET.get("days", 7))
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


# â”€â”€ GA4 Data API (Reporting) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@require_GET
def ga4_organic_traffic(request, site_id: int) -> JsonResponse:
    """Get organic traffic data from GA4 Data API.

    GET /api/analytics/<site_id>/ga4-organic/?days=30
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    days = int(request.GET.get("days", 30))
    client = _get_ga4_report_client(site)
    data = client.get_organic_traffic(days=days)
    return JsonResponse({"success": True, "data": data, "count": len(data)})


@require_GET
def ga4_conversions(request, site_id: int) -> JsonResponse:
    """Get conversion event data from GA4 Data API.

    GET /api/analytics/<site_id>/ga4-conversions/?days=30
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    days = int(request.GET.get("days", 30))
    client = _get_ga4_report_client(site)
    data = client.get_conversion_events(days=days)
    return JsonResponse({"success": True, "data": data, "count": len(data)})


@require_GET
def ga4_top_pages(request, site_id: int) -> JsonResponse:
    """Get top pages from GA4 Data API.

    GET /api/analytics/<site_id>/ga4-pages/?days=30&limit=50
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    days = int(request.GET.get("days", 30))
    limit = int(request.GET.get("limit", 50))
    client = _get_ga4_report_client(site)
    data = client.get_top_pages(days=days, limit=limit)
    return JsonResponse({"success": True, "data": data, "count": len(data)})


@require_GET
def ga4_traffic_sources(request, site_id: int) -> JsonResponse:
    """Get traffic source breakdown from GA4 Data API.

    GET /api/analytics/<site_id>/ga4-sources/?days=30
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    days = int(request.GET.get("days", 30))
    client = _get_ga4_report_client(site)
    data = client.get_traffic_sources(days=days)
    return JsonResponse({"success": True, "data": data, "count": len(data)})


# â”€â”€ GA4 Admin API (Key Events) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@require_GET
def ga4_key_events(request, site_id: int) -> JsonResponse:
    """List all Key Events (conversions) in GA4.

    GET /api/analytics/<site_id>/key-events/
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    client = _get_ga4_admin_client(site)
    result = client.list_key_events()
    return JsonResponse(result)


@require_POST
def ga4_create_key_event(request, site_id: int) -> JsonResponse:
    """Mark an event as a Key Event in GA4.

    POST /api/analytics/<site_id>/key-events/create/
    Body: {"event_name": "purchase", "counting_method": "ONCE_PER_EVENT"}
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    event_name = body.get("event_name", "")
    counting = body.get("counting_method", "ONCE_PER_EVENT")

    if not event_name:
        return JsonResponse({"error": "event_name is required"}, status=400)

    client = _get_ga4_admin_client(site)
    result = client.create_key_event(event_name, counting_method=counting)
    return JsonResponse(result)


@require_POST
def ga4_delete_key_event(request, site_id: int) -> JsonResponse:
    """Delete (unmark) a Key Event in GA4.

    POST /api/analytics/<site_id>/key-events/delete/
    Body: {"key_event_name": "properties/123/keyEvents/456"}
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    key_event_name = body.get("key_event_name", "")

    if not key_event_name:
        return JsonResponse({"error": "key_event_name is required"}, status=400)

    client = _get_ga4_admin_client(site)
    result = client.delete_key_event(key_event_name)
    return JsonResponse(result)


@require_POST
def ga4_mark_beezle_events(request, site_id: int) -> JsonResponse:
    """Mark all Beezle standard events as Key Events.

    POST /api/analytics/<site_id>/key-events/mark-beezle/
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    client = _get_ga4_admin_client(site)
    results = client.mark_beezle_key_events()
    return JsonResponse({"results": results, "count": len(results)})


# â”€â”€ GSC Sitemap Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@require_GET
def gsc_sitemaps(request, site_id: int) -> JsonResponse:
    """List all sitemaps registered in GSC.

    GET /api/analytics/<site_id>/sitemaps/
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    client = _get_gsc_client(site)
    result = client.list_sitemaps()
    return JsonResponse(result)


@require_POST
def gsc_submit_sitemap(request, site_id: int) -> JsonResponse:
    """Submit a sitemap to GSC.

    POST /api/analytics/<site_id>/sitemaps/submit/
    Body: {"sitemap_url": "https://beezle.io/sitemap.xml"}
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    sitemap_url = body.get("sitemap_url", site.sitemap_url or "")

    if not sitemap_url:
        return JsonResponse({"error": "sitemap_url is required"}, status=400)

    client = _get_gsc_client(site)
    result = client.submit_sitemap(sitemap_url)
    return JsonResponse(result)


@require_POST
def gsc_delete_sitemap(request, site_id: int) -> JsonResponse:
    """Delete a sitemap from GSC.

    POST /api/analytics/<site_id>/sitemaps/delete/
    Body: {"sitemap_url": "https://beezle.io/sitemap.xml"}
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    sitemap_url = body.get("sitemap_url", "")

    if not sitemap_url:
        return JsonResponse({"error": "sitemap_url is required"}, status=400)

    client = _get_gsc_client(site)
    result = client.delete_sitemap(sitemap_url)
    return JsonResponse(result)


# â”€â”€ GSC URL Indexing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@require_POST
def gsc_submit_url(request, site_id: int) -> JsonResponse:
    """Submit a URL for indexing via Indexing API.

    POST /api/analytics/<site_id>/indexing/submit/
    Body: {"url": "https://beezle.io/blog/post-1/"}
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    url = body.get("url", "")

    if not url:
        return JsonResponse({"error": "url is required"}, status=400)

    client = _get_gsc_client(site)
    result = client.submit_url_for_indexing(url)
    return JsonResponse(result)


@require_POST
def gsc_batch_submit_urls(request, site_id: int) -> JsonResponse:
    """Submit multiple URLs for indexing.

    POST /api/analytics/<site_id>/indexing/batch/
    Body: {"urls": ["https://beezle.io/blog/post-1/", ...]}
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    urls = body.get("urls", [])

    if not urls:
        return JsonResponse({"error": "urls list is required"}, status=400)

    client = _get_gsc_client(site)
    results = client.batch_submit_urls(urls)
    return JsonResponse({"results": results, "count": len(results)})


@require_POST
def gsc_remove_url(request, site_id: int) -> JsonResponse:
    """Request removal of a URL from the index.

    POST /api/analytics/<site_id>/indexing/remove/
    Body: {"url": "https://beezle.io/old-page/"}
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    url = body.get("url", "")

    if not url:
        return JsonResponse({"error": "url is required"}, status=400)

    client = _get_gsc_client(site)
    result = client.remove_url_from_index(url)
    return JsonResponse(result)


# â”€â”€ GSC URL Inspection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@require_POST
def gsc_inspect_url(request, site_id: int) -> JsonResponse:
    """Inspect a URL's index status.

    POST /api/analytics/<site_id>/inspect/
    Body: {"url": "https://beezle.io/blog/post-1/"}
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    url = body.get("url", "")

    if not url:
        return JsonResponse({"error": "url is required"}, status=400)

    client = _get_gsc_client(site)
    result = client.inspect_url(url)
    return JsonResponse(result)


@require_POST
def gsc_batch_inspect(request, site_id: int) -> JsonResponse:
    """Inspect multiple URLs for index status.

    POST /api/analytics/<site_id>/inspect/batch/
    Body: {"urls": ["https://beezle.io/blog/post-1/", ...]}
    """
    site = _get_site(site_id)
    if not site:
        return JsonResponse({"error": "Site not found"}, status=404)

    body = json.loads(request.body)
    urls = body.get("urls", [])

    if not urls:
        return JsonResponse({"error": "urls list is required"}, status=400)

    client = _get_gsc_client(site)
    results = client.batch_inspect_urls(urls)
    return JsonResponse({"results": results, "count": len(results)})

