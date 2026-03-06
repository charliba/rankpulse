"""Core views — Dashboard, Project/Site CRUD, reports, and integrations."""
from __future__ import annotations

import json
import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Sum
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import GA4EventForm, IntegrationsForm, KPIGoalForm, ProjectForm, SiteForm
from .models import GA4EventDefinition, KPIGoal, Project, Site, WeeklySnapshot

logger = logging.getLogger(__name__)


def _base_context(request) -> dict:
    """Common context for all views — user's projects for sidebar."""
    projects = Project.objects.filter(owner=request.user, is_active=True).prefetch_related("sites")
    return {"projects": projects}


def _get_user_project(request, project_id: int) -> Project:
    """Get a project that belongs to the current user."""
    return get_object_or_404(Project, pk=project_id, owner=request.user)


def _get_user_site(request, site_id: int) -> Site:
    """Get a site whose project belongs to the current user."""
    return get_object_or_404(
        Site.objects.select_related("project"),
        pk=site_id,
        project__owner=request.user,
    )


# ── Dashboard ──────────────────────────────────────────

@login_required
def dashboard(request):
    """Main dashboard showing user's projects overview."""
    projects = Project.objects.filter(owner=request.user, is_active=True).prefetch_related(
        "sites", "channels",
    )

    project_data = []
    for project in projects:
        sites = project.sites.filter(is_active=True)
        channels = project.channels.filter(is_active=True)

        site_data = []
        for site in sites:
            latest_snapshot = site.weekly_snapshots.first()
            events_total = site.event_definitions.count()
            events_implemented = site.event_definitions.filter(is_implemented=True).count()
            site_data.append({
                "site": site,
                "snapshot": latest_snapshot,
                "events_total": events_total,
                "events_implemented": events_implemented,
                "events_pct": (events_implemented / events_total * 100) if events_total else 0,
            })

        project_data.append({
            "project": project,
            "sites": site_data,
            "channels": channels,
            "total_sites": sites.count(),
            "total_channels": channels.count(),
        })

    context = {
        **_base_context(request),
        "page_title": "Dashboard",
        "project_data": project_data,
        "total_projects": projects.count(),
    }
    return render(request, "core/dashboard.html", context)


# ── Project CRUD ───────────────────────────────────────

@login_required
def project_add(request):
    """Create a new project."""
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            messages.success(request, f"Projeto '{project.name}' criado com sucesso!")
            return redirect("core:project_detail", project_id=project.pk)
    else:
        form = ProjectForm()

    context = {
        **_base_context(request),
        "page_title": "Novo Projeto",
        "form": form,
    }
    return render(request, "core/project_form.html", context)


@login_required
def project_detail(request, project_id: int):
    """Detailed view of a project — its sites and channels."""
    project = _get_user_project(request, project_id)
    sites = project.sites.filter(is_active=True)
    channels = project.channels.filter(is_active=True)

    site_data = []
    for site in sites:
        latest_snapshot = site.weekly_snapshots.first()
        events_total = site.event_definitions.count()
        events_implemented = site.event_definitions.filter(is_implemented=True).count()
        site_data.append({
            "site": site,
            "snapshot": latest_snapshot,
            "events_total": events_total,
            "events_implemented": events_implemented,
            "events_pct": (events_implemented / events_total * 100) if events_total else 0,
        })

    context = {
        **_base_context(request),
        "page_title": project.name,
        "project": project,
        "site_data": site_data,
        "channels": channels,
    }
    return render(request, "core/project_detail.html", context)


@login_required
def project_edit(request, project_id: int):
    """Edit an existing project."""
    project = _get_user_project(request, project_id)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Projeto '{project.name}' atualizado!")
            return redirect("core:project_detail", project_id=project.pk)
    else:
        form = ProjectForm(instance=project)

    context = {
        **_base_context(request),
        "page_title": f"Editar {project.name}",
        "form": form,
        "project": project,
        "editing": True,
    }
    return render(request, "core/project_form.html", context)


@login_required
def project_delete(request, project_id: int):
    """Delete a project (POST only)."""
    project = _get_user_project(request, project_id)
    if request.method == "POST":
        name = project.name
        project.delete()
        messages.success(request, f"Projeto '{name}' removido.")
        return redirect("core:dashboard")
    return redirect("core:project_detail", project_id=project.pk)


# ── Site CRUD ──────────────────────────────────────────

@login_required
def site_add(request, project_id: int):
    """Create a new site inside a project."""
    project = _get_user_project(request, project_id)

    if request.method == "POST":
        form = SiteForm(request.POST)
        if form.is_valid():
            site = form.save(commit=False)
            site.project = project
            site.save()
            messages.success(request, f"Site '{site.name}' criado com sucesso!")
            return redirect("core:site_detail", site_id=site.pk)
    else:
        form = SiteForm()

    context = {
        **_base_context(request),
        "page_title": "Adicionar Site",
        "form": form,
        "project": project,
    }
    return render(request, "core/site_form.html", context)


@login_required
def site_edit(request, site_id: int):
    """Edit an existing site."""
    site = _get_user_site(request, site_id)
    if request.method == "POST":
        form = SiteForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, f"Site '{site.name}' atualizado!")
            return redirect("core:site_detail", site_id=site.pk)
    else:
        form = SiteForm(instance=site)

    context = {
        **_base_context(request),
        "page_title": f"Editar {site.name}",
        "form": form,
        "site": site,
        "project": site.project,
        "editing": True,
    }
    return render(request, "core/site_form.html", context)


@login_required
def site_delete(request, site_id: int):
    """Delete a site (POST only)."""
    site = _get_user_site(request, site_id)
    project_id = site.project_id
    if request.method == "POST":
        name = site.name
        site.delete()
        messages.success(request, f"Site '{name}' removido.")
        return redirect("core:project_detail", project_id=project_id)
    return redirect("core:site_detail", site_id=site.pk)


# ── Site Detail ────────────────────────────────────────

@login_required
def site_detail(request, site_id: int):
    """Detailed view of a single site's traffic data."""
    site = _get_user_site(request, site_id)
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
        **_base_context(request),
        "page_title": site.name,
        "site": site,
        "project": site.project,
        "snapshots": snapshots,
        "events_pending": events_pending,
        "events_done": events_done,
        "kpis_by_period": kpis_by_period,
    }
    return render(request, "core/site_detail.html", context)


# ── Weekly Report ──────────────────────────────────────

@login_required
def weekly_report(request, site_id: int):
    """Weekly report form and history."""
    site = _get_user_site(request, site_id)
    snapshots = site.weekly_snapshots.all()[:26]

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
        messages.success(request, "Relatório salvo com sucesso!")
        return redirect("core:weekly_report", site_id=site.pk)

    context = {
        **_base_context(request),
        "page_title": "Relatório Semanal",
        "site": site,
        "snapshots": snapshots,
    }
    return render(request, "core/weekly_report.html", context)


# ── GA4 Events CRUD ───────────────────────────────────

@login_required
def event_add(request, site_id: int):
    """Add a GA4 event to a site."""
    site = _get_user_site(request, site_id)
    if request.method == "POST":
        form = GA4EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.site = site
            event.save()
            messages.success(request, f"Evento '{event.event_name}' criado!")
            return redirect("core:site_detail", site_id=site.pk)
    else:
        form = GA4EventForm()

    context = {
        **_base_context(request),
        "page_title": "Adicionar Evento",
        "form": form,
        "site": site,
    }
    return render(request, "core/event_form.html", context)


@login_required
def event_edit(request, site_id: int, event_id: int):
    """Edit a GA4 event."""
    site = _get_user_site(request, site_id)
    event = get_object_or_404(GA4EventDefinition, pk=event_id, site=site)
    if request.method == "POST":
        form = GA4EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f"Evento '{event.event_name}' atualizado!")
            return redirect("core:site_detail", site_id=site.pk)
    else:
        form = GA4EventForm(instance=event)

    context = {
        **_base_context(request),
        "page_title": f"Editar {event.event_name}",
        "form": form,
        "site": site,
        "event": event,
        "editing": True,
    }
    return render(request, "core/event_form.html", context)


@login_required
def event_delete(request, site_id: int, event_id: int):
    """Delete a GA4 event (POST only)."""
    site = _get_user_site(request, site_id)
    event = get_object_or_404(GA4EventDefinition, pk=event_id, site=site)
    if request.method == "POST":
        name = event.event_name
        event.delete()
        messages.success(request, f"Evento '{name}' removido.")
    return redirect("core:site_detail", site_id=site.pk)


# ── KPI Goals CRUD ────────────────────────────────────

@login_required
def kpi_add(request, site_id: int):
    """Add a KPI goal to a site."""
    site = _get_user_site(request, site_id)
    if request.method == "POST":
        form = KPIGoalForm(request.POST)
        if form.is_valid():
            kpi = form.save(commit=False)
            kpi.site = site
            kpi.save()
            messages.success(request, f"Meta '{kpi.metric_name}' criada!")
            return redirect("core:site_detail", site_id=site.pk)
    else:
        form = KPIGoalForm()

    context = {
        **_base_context(request),
        "page_title": "Adicionar Meta KPI",
        "form": form,
        "site": site,
    }
    return render(request, "core/kpi_form.html", context)


@login_required
def kpi_edit(request, site_id: int, kpi_id: int):
    """Edit a KPI goal."""
    site = _get_user_site(request, site_id)
    kpi = get_object_or_404(KPIGoal, pk=kpi_id, site=site)
    if request.method == "POST":
        form = KPIGoalForm(request.POST, instance=kpi)
        if form.is_valid():
            form.save()
            messages.success(request, f"Meta '{kpi.metric_name}' atualizada!")
            return redirect("core:site_detail", site_id=site.pk)
    else:
        form = KPIGoalForm(instance=kpi)

    context = {
        **_base_context(request),
        "page_title": f"Editar {kpi.metric_name}",
        "form": form,
        "site": site,
        "kpi": kpi,
        "editing": True,
    }
    return render(request, "core/kpi_form.html", context)


@login_required
def kpi_delete(request, site_id: int, kpi_id: int):
    """Delete a KPI goal (POST only)."""
    site = _get_user_site(request, site_id)
    kpi = get_object_or_404(KPIGoal, pk=kpi_id, site=site)
    if request.method == "POST":
        name = kpi.metric_name
        kpi.delete()
        messages.success(request, f"Meta '{name}' removida.")
    return redirect("core:site_detail", site_id=site.pk)


# ── Auth: Register ─────────────────────────────────────

def register(request):
    """First-access user registration."""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        errors: list[str] = []

        if not username:
            errors.append("Informe um nome de usuário.")
        if not email:
            errors.append("Informe um e-mail.")
        if len(password) < 6:
            errors.append("A senha deve ter pelo menos 6 caracteres.")
        if password != password2:
            errors.append("As senhas não coincidem.")
        if User.objects.filter(username=username).exists():
            errors.append("Esse nome de usuário já está em uso.")
        if User.objects.filter(email=email).exists():
            errors.append("Esse e-mail já está cadastrado.")

        if errors:
            return render(request, "pages/auth.html", {
                "tab": "register",
                "reg_errors": errors,
                "reg_username": username,
                "reg_email": email,
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        login(request, user)
        messages.success(request, f"Bem-vindo, {user.username}! Conta criada com sucesso.")
        return redirect("/")

    return render(request, "pages/auth.html", {"tab": "register"})


# ── Integrations ──────────────────────────────────────

@login_required
def site_integrations(request, site_id: int):
    """Integrations settings page — GA4, GSC credentials."""
    site = _get_user_site(request, site_id)

    if request.method == "POST":
        form = IntegrationsForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, "Integrações salvas com sucesso!")
            return redirect("core:site_integrations", site_id=site.pk)
    else:
        form = IntegrationsForm(instance=site)

    integrations_status = {
        "ga4": bool(site.ga4_measurement_id),
        "ga4_api": bool(site.ga4_api_secret),
        "ga4_property": bool(site.ga4_property_id),
        "ga4_service_account": bool(site.ga4_service_account_key),
        "gsc": site.gsc_verified,
        "gsc_service_account": bool(site.gsc_service_account_key),
    }

    context = {
        **_base_context(request),
        "page_title": "Integrações",
        "site": site,
        "project": site.project,
        "form": form,
        "status": integrations_status,
    }
    return render(request, "core/site_integrations.html", context)
