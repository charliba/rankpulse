"""Core views — Dashboard and main pages."""
from __future__ import annotations

from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import GA4EventDefinition, KPIGoal, Site, WeeklySnapshot


def dashboard(request):
    """Main dashboard showing all managed sites overview."""
    sites = Site.objects.filter(is_active=True)
    site_data = []

    for site in sites:
        latest_snapshot = site.weekly_snapshots.first()
        events_total = site.event_definitions.count()
        events_implemented = site.event_definitions.filter(is_implemented=True).count()
        kpi_goals = site.kpi_goals.filter(period="month_3")

        site_data.append({
            "site": site,
            "snapshot": latest_snapshot,
            "events_total": events_total,
            "events_implemented": events_implemented,
            "events_pct": (events_implemented / events_total * 100) if events_total else 0,
            "kpi_goals": kpi_goals,
        })

    context = {
        "site_data": site_data,
        "total_sites": sites.count(),
    }
    return render(request, "core/dashboard.html", context)


def site_detail(request, site_id: int):
    """Detailed view of a single site's traffic data."""
    site = get_object_or_404(Site, pk=site_id, is_active=True)
    snapshots = site.weekly_snapshots.all()[:12]
    events = site.event_definitions.all()
    kpi_goals = site.kpi_goals.all()

    # Group KPIs by period
    kpis_by_period: dict[str, list] = {}
    for kpi in kpi_goals:
        period = kpi.get_period_display()
        kpis_by_period.setdefault(period, []).append(kpi)

    # Events by status
    events_pending = events.filter(is_implemented=False).order_by("priority")
    events_done = events.filter(is_implemented=True)

    context = {
        "site": site,
        "snapshots": snapshots,
        "events_pending": events_pending,
        "events_done": events_done,
        "kpis_by_period": kpis_by_period,
    }
    return render(request, "core/site_detail.html", context)


def weekly_report(request, site_id: int):
    """Weekly report form and history."""
    site = get_object_or_404(Site, pk=site_id, is_active=True)
    snapshots = site.weekly_snapshots.all()[:26]  # 6 months

    if request.method == "POST":
        today = timezone.now().date()
        week_start = today - timezone.timedelta(days=today.weekday())
        week_end = week_start + timezone.timedelta(days=6)

        snapshot, _ = WeeklySnapshot.objects.update_or_create(
            site=site,
            week_start=week_start,
            defaults={
                "week_end": week_end,
                "organic_sessions": int(request.POST.get("organic_sessions", 0)),
                "total_sessions": int(request.POST.get("total_sessions", 0)),
                "signups": int(request.POST.get("signups", 0)),
                "purchases": int(request.POST.get("purchases", 0)),
                "revenue": request.POST.get("revenue", 0),
                "gsc_impressions": int(request.POST.get("gsc_impressions", 0)),
                "gsc_clicks": int(request.POST.get("gsc_clicks", 0)),
                "gsc_ctr": request.POST.get("gsc_ctr", 0),
                "gsc_position": request.POST.get("gsc_position", 0),
                "keywords_top10": int(request.POST.get("keywords_top10", 0)),
                "posts_published": int(request.POST.get("posts_published", 0)),
                "backlinks": int(request.POST.get("backlinks", 0)),
                "highlights": request.POST.get("highlights", ""),
                "issues": request.POST.get("issues", ""),
                "next_steps": request.POST.get("next_steps", ""),
            },
        )

    context = {
        "site": site,
        "snapshots": snapshots,
    }
    return render(request, "core/weekly_report.html", context)
