"""Core views — Dashboard, Project/Site CRUD, reports, and integrations."""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Avg, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST


def login_view(request):
    """GET — exibe login. POST — autentica (padrão waLink/askJoel)."""
    if request.method == "GET":
        return render(request, "pages/auth.html", {"form": AuthenticationForm()})

    form = AuthenticationForm(request, data=request.POST)
    if form.is_valid():
        user = form.get_user()
        request.session.flush()
        login(request, user)
        logger.info("Login: %s", user.username)
        next_url = request.POST.get("next") or request.GET.get("next") or settings.LOGIN_REDIRECT_URL
        return redirect(next_url)

    return render(request, "pages/auth.html", {"form": form})


def _parse_days(request, default=7):
    """Parse days from request GET param, clamped to valid range."""
    try:
        d = int(request.GET.get("days", default))
    except (ValueError, TypeError):
        d = default
    return max(1, min(d, 90))

from .forms import GA4EventForm, IntegrationsForm, KPIGoalForm, ProjectForm, SiteForm
from .models import GA4EventDefinition, KPIGoal, Project, Site, WeeklySnapshot

logger = logging.getLogger(__name__)


def _base_context(request) -> dict:
    """Common context for all views — user's projects for sidebar."""
    projects = Project.objects.filter(owner=request.user, is_active=True).prefetch_related("sites")
    return {"projects": projects}


def _get_user_project(request, project_id: int) -> Project:
    """Get a project that belongs to the current user (or any project for superusers)."""
    if request.user.is_superuser:
        return get_object_or_404(Project, pk=project_id)
    return get_object_or_404(Project, pk=project_id, owner=request.user)


def _get_user_site(request, site_id: int) -> Site:
    """Get a site whose project belongs to the current user (or any site for superusers)."""
    qs = Site.objects.select_related("project")
    if request.user.is_superuser:
        return get_object_or_404(qs, pk=site_id)
    return get_object_or_404(qs, pk=site_id, project__owner=request.user)


# ── Public Pages ───────────────────────────────────────


def landing_view(request):
    """Public landing page — redirects to app subdomain if already logged in."""
    if request.user.is_authenticated:
        return redirect(f"{settings.APP_URL}/dashboard/")
    return render(request, "pages/landing.html", {
        "year": date.today().year,
    })


def privacy_view(request):
    """Public privacy policy page."""
    return render(request, "pages/privacy.html", {
        "year": date.today().year,
        "today": date.today().strftime("%B %d, %Y"),
    })


def terms_view(request):
    """Public terms of service page."""
    return render(request, "pages/terms.html", {
        "year": date.today().year,
        "today": date.today().strftime("%B %d, %Y"),
    })


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
        "page_id": "global_dashboard",
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
            messages.success(request, f"Projeto '{project.name}' criado! Vamos configurar.")
            return redirect("core:project_onboarding", project_id=project.pk)
    else:
        form = ProjectForm()

    context = {
        **_base_context(request),
        "page_title": "Novo Projeto",
        "form": form,
    }
    return render(request, "core/project_form.html", context)


@login_required
def project_onboarding(request, project_id: int):
    """Guided onboarding wizard for a new project."""
    project = _get_user_project(request, project_id)
    sites = project.sites.filter(is_active=True)
    channels = project.channels.filter(is_active=True)

    has_site = sites.exists()
    has_ga4 = sites.filter(ga4_property_id__gt="").exists()
    has_gsc = sites.filter(gsc_site_url__gt="").exists()
    has_google_ads = channels.filter(platform="google_ads").exists()
    has_meta_ads = channels.filter(platform="meta_ads").exists()

    # Determine current step
    if not has_site:
        step = 1
    elif not has_ga4 and not has_gsc:
        step = 2
    elif not has_google_ads and not has_meta_ads:
        step = 3
    else:
        step = 4  # All done

    context = {
        **_base_context(request),
        "page_title": f"Configurar {project.name}",
        "page_id": "project_onboarding",
        "project": project,
        "step": step,
        "has_site": has_site,
        "has_ga4": has_ga4,
        "has_gsc": has_gsc,
        "has_google_ads": has_google_ads,
        "has_meta_ads": has_meta_ads,
        "sites": sites,
    }
    return render(request, "core/project_onboarding.html", context)


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
        "page_id": "project_sites",
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
        return redirect("core:dashboard")

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

    from django.conf import settings as app_settings
    integrations_status = {
        "ga4": bool(site.ga4_measurement_id),
        "ga4_api": bool(site.ga4_api_secret),
        "ga4_property": bool(site.ga4_property_id),
        "google_connected": bool(site.google_refresh_token),
        "gsc": bool(site.gsc_site_url),
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


# ── Google OAuth (GA4 + GSC) ─────────────────────────

import os
import urllib.parse

import requests as http_requests

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_ANALYTICS_SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/analytics.edit",
    "https://www.googleapis.com/auth/webmasters.readonly",
]


def _get_google_oauth_config():
    """Return OAuth client_id, client_secret, redirect_uri from settings."""
    from django.conf import settings as s
    client_id = s.GOOGLE_ADS_CLIENT_ID
    client_secret = s.GOOGLE_ADS_CLIENT_SECRET
    app_domain = os.environ.get("APP_DOMAIN", "rankpulse.cloud")
    redirect_uri = f"https://app.{app_domain}/integrations/oauth/google/callback/"
    return client_id, client_secret, redirect_uri


def _refresh_google_access_token(site):
    """Exchange refresh_token for a fresh access_token. Returns the token string."""
    client_id, client_secret, _ = _get_google_oauth_config()
    resp = http_requests.post(GOOGLE_TOKEN_URI, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": site.google_refresh_token,
        "grant_type": "refresh_token",
    }, timeout=15)
    data = resp.json()
    access_token = data.get("access_token", "")
    if access_token:
        site.google_access_token = access_token
        site.save(update_fields=["google_access_token"])
    return access_token


@login_required
def google_oauth_start(request, site_id: int):
    """Redirect user to Google OAuth2 for GA4 + Search Console access."""
    site = _get_user_site(request, site_id)
    client_id, _, redirect_uri = _get_google_oauth_config()

    if not client_id:
        messages.error(request, "OAuth Client ID não configurado.")
        return redirect("core:site_integrations", site_id=site.pk)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(GOOGLE_ANALYTICS_SCOPES),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "state": str(site.pk),
    }
    auth_url = f"{GOOGLE_AUTH_URI}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


@login_required
def google_oauth_callback(request):
    """Handle Google OAuth2 callback — exchange code for tokens."""
    code = request.GET.get("code", "")
    error = request.GET.get("error", "")
    state = request.GET.get("state", "")

    if not state:
        messages.error(request, "Parâmetro state ausente no callback.")
        return redirect("core:dashboard")

    site_id = int(state)
    site = _get_user_site(request, site_id)

    if error:
        messages.error(request, f"Google OAuth negado: {error}")
        return redirect("core:site_integrations", site_id=site.pk)

    if not code:
        messages.error(request, "Código de autorização não recebido do Google.")
        return redirect("core:site_integrations", site_id=site.pk)

    client_id, client_secret, redirect_uri = _get_google_oauth_config()

    try:
        resp = http_requests.post(GOOGLE_TOKEN_URI, data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=30)
        token_data = resp.json()
    except Exception as exc:
        logger.exception("Google OAuth token exchange failed")
        messages.error(request, f"Erro ao contatar o Google: {exc}")
        return redirect("core:site_integrations", site_id=site.pk)

    if "error" in token_data:
        messages.error(request, f"Google retornou erro: {token_data.get('error_description', token_data['error'])}")
        return redirect("core:site_integrations", site_id=site.pk)

    refresh_token = token_data.get("refresh_token", "")
    if not refresh_token:
        messages.error(request, "Google não retornou refresh_token. Tente novamente.")
        return redirect("core:site_integrations", site_id=site.pk)

    site.google_refresh_token = refresh_token
    site.google_access_token = token_data.get("access_token", "")
    site.save(update_fields=["google_refresh_token", "google_access_token"])

    messages.success(request, "Google conectado com sucesso! Selecione a propriedade GA4.")
    return redirect("core:google_select_property", site_id=site.pk)


@login_required
def google_select_property(request, site_id: int):
    """List GA4 properties the user has access to and let them pick one."""
    site = _get_user_site(request, site_id)

    if not site.google_refresh_token:
        messages.error(request, "Conecte sua conta Google primeiro.")
        return redirect("core:site_integrations", site_id=site.pk)

    access_token = site.google_access_token or _refresh_google_access_token(site)
    if not access_token:
        messages.error(request, "Não foi possível obter access token. Reconecte o Google.")
        return redirect("core:site_integrations", site_id=site.pk)

    if request.method == "POST":
        selected = request.POST.get("property_id", "")
        measurement_id = request.POST.get("measurement_id", "")
        if selected:
            site.ga4_property_id = selected
            if measurement_id:
                site.ga4_measurement_id = measurement_id
            site.save(update_fields=["ga4_property_id", "ga4_measurement_id"])
            messages.success(request, f"Propriedade GA4 {selected} selecionada!")
            return redirect("core:google_select_gsc_site", site_id=site.pk)
        messages.error(request, "Selecione uma propriedade.")

    # List GA4 accounts and properties via Admin API
    properties = []
    error_msg = ""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        # List account summaries
        resp = http_requests.get(
            "https://analyticsadmin.googleapis.com/v1beta/accountSummaries",
            headers=headers, timeout=15,
        )
        if resp.status_code == 401:
            access_token = _refresh_google_access_token(site)
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = http_requests.get(
                "https://analyticsadmin.googleapis.com/v1beta/accountSummaries",
                headers=headers, timeout=15,
            )
        data = resp.json()
        for account in data.get("accountSummaries", []):
            account_name = account.get("displayName", "")
            for prop in account.get("propertySummaries", []):
                prop_id = prop.get("property", "").replace("properties/", "")
                properties.append({
                    "id": prop_id,
                    "name": prop.get("displayName", ""),
                    "account": account_name,
                })
    except Exception as exc:
        error_msg = str(exc)
        logger.exception("Failed to list GA4 properties")

    # Try to get measurement IDs for each property via data streams
    for prop in properties:
        try:
            resp = http_requests.get(
                f"https://analyticsadmin.googleapis.com/v1beta/properties/{prop['id']}/dataStreams",
                headers={"Authorization": f"Bearer {access_token}"}, timeout=10,
            )
            streams = resp.json().get("dataStreams", [])
            for stream in streams:
                if stream.get("type") == "WEB_DATA_STREAM":
                    web = stream.get("webStreamData", {})
                    prop["measurement_id"] = web.get("measurementId", "")
                    prop["stream_url"] = web.get("defaultUri", "")
                    break
        except Exception:
            pass

    context = {
        **_base_context(request),
        "page_title": "Selecionar Propriedade GA4",
        "site": site,
        "project": site.project,
        "properties": properties,
        "error_msg": error_msg,
    }
    return render(request, "core/google_select_property.html", context)


@login_required
def google_select_gsc_site(request, site_id: int):
    """List Search Console sites the user has access to and let them pick one."""
    site = _get_user_site(request, site_id)

    if not site.google_refresh_token:
        messages.error(request, "Conecte sua conta Google primeiro.")
        return redirect("core:site_integrations", site_id=site.pk)

    access_token = site.google_access_token or _refresh_google_access_token(site)

    if request.method == "POST":
        selected = request.POST.get("site_url", "")
        if selected:
            site.gsc_site_url = selected
            site.gsc_verified = True
            site.save(update_fields=["gsc_site_url", "gsc_verified"])
            messages.success(request, f"Site GSC selecionado: {selected}")
            return redirect("core:site_integrations", site_id=site.pk)
        messages.error(request, "Selecione um site.")

    # List GSC sites
    gsc_sites = []
    error_msg = ""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = http_requests.get(
            "https://www.googleapis.com/webmasters/v3/sites",
            headers=headers, timeout=15,
        )
        if resp.status_code == 401:
            access_token = _refresh_google_access_token(site)
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = http_requests.get(
                "https://www.googleapis.com/webmasters/v3/sites",
                headers=headers, timeout=15,
            )
        data = resp.json()
        for entry in data.get("siteEntry", []):
            gsc_sites.append({
                "url": entry.get("siteUrl", ""),
                "permission": entry.get("permissionLevel", ""),
            })
    except Exception as exc:
        error_msg = str(exc)
        logger.exception("Failed to list GSC sites")

    context = {
        **_base_context(request),
        "page_title": "Selecionar Site GSC",
        "site": site,
        "project": site.project,
        "gsc_sites": gsc_sites,
        "error_msg": error_msg,
    }
    return render(request, "core/google_select_gsc_site.html", context)


@login_required
def google_disconnect(request, site_id: int):
    """Remove Google OAuth connection from a site."""
    site = _get_user_site(request, site_id)
    site.google_refresh_token = ""
    site.google_access_token = ""
    site.save(update_fields=["google_refresh_token", "google_access_token"])
    messages.success(request, "Google desconectado.")
    return redirect("core:site_integrations", site_id=site.pk)

# ── Project Sub-Pages ──────────────────────────────────

@login_required
def project_dashboard(request, project_id: int):
    """Project dashboard — real-time metrics from all connected sources."""
    from .models import ProjectScore

    project = _get_user_project(request, project_id)
    sites = project.sites.filter(is_active=True)
    channels = project.channels.filter(is_active=True)

    # Determine connection status for each source type
    has_ga4 = sites.filter(ga4_property_id__gt="").exists()
    has_gsc = sites.filter(gsc_site_url__gt="").exists()
    has_google_ads = channels.filter(platform="google_ads").exists()
    has_meta_ads = channels.filter(platform="meta_ads").exists()

    google_ads_channel = channels.filter(platform="google_ads").first()
    meta_ads_channel = channels.filter(platform="meta_ads").first()

    # Gamification score
    project_score = ProjectScore.objects.filter(project=project).first()

    context = {
        **_base_context(request),
        "page_title": f"Dashboard — {project.name}",
        "page_id": "project_dashboard",
        "project": project,
        "sites": sites,
        "channels": channels,
        "has_ga4": has_ga4,
        "has_gsc": has_gsc,
        "has_google_ads": has_google_ads and google_ads_channel and google_ads_channel.is_configured,
        "has_meta_ads": has_meta_ads and meta_ads_channel and meta_ads_channel.is_configured,
        "google_ads_channel": google_ads_channel,
        "meta_ads_channel": meta_ads_channel,
        "project_score": project_score,
    }
    return render(request, "core/project_dashboard.html", context)


@login_required
def project_sources(request, project_id: int):
    """Unified sources page — visual cards for GA4, GSC, Google Ads, Meta Ads."""
    project = _get_user_project(request, project_id)
    sites = project.sites.filter(is_active=True)
    channels = project.channels.filter(is_active=True)

    google_ads_channel = channels.filter(platform="google_ads").first()
    meta_ads_channel = channels.filter(platform="meta_ads").first()

    sources = []
    # GA4 sources (per site)
    for site in sites:
        sources.append({
            "type": "ga4",
            "label": "Google Analytics 4",
            "site": site,
            "connected": bool(site.ga4_property_id and site.google_refresh_token),
            "detail": site.ga4_property_id or "Não conectado",
            "connect_url": (
                f"/site/{site.pk}/integrations/"
                if not site.google_refresh_token
                else ""
            ),
        })
        sources.append({
            "type": "gsc",
            "label": "Search Console",
            "site": site,
            "connected": bool(site.gsc_site_url and site.google_refresh_token),
            "detail": site.gsc_site_url or "Não conectado",
            "connect_url": (
                f"/site/{site.pk}/integrations/"
                if not site.google_refresh_token
                else ""
            ),
        })

    # Google Ads (per project)
    sources.append({
        "type": "google_ads",
        "label": "Google Ads",
        "site": None,
        "connected": bool(google_ads_channel and google_ads_channel.is_configured),
        "detail": (
            google_ads_channel.credentials.customer_id
            if google_ads_channel and google_ads_channel.is_configured
            else "Não conectado"
        ),
        "channel": google_ads_channel,
    })

    # Meta Ads (per project)
    sources.append({
        "type": "meta_ads",
        "label": "Meta Ads",
        "site": None,
        "connected": bool(meta_ads_channel and meta_ads_channel.is_configured),
        "detail": (
            meta_ads_channel.credentials.account_id
            if meta_ads_channel and meta_ads_channel.is_configured
            else "Não conectado"
        ),
        "channel": meta_ads_channel,
    })

    context = {
        **_base_context(request),
        "page_title": f"Fontes — {project.name}",
        "page_id": "project_sources",
        "project": project,
        "sources": sources,
        "sites": sites,
        "google_ads_channel": google_ads_channel,
        "meta_ads_channel": meta_ads_channel,
    }
    return render(request, "core/project_sources.html", context)


@login_required
def project_campaigns(request, project_id: int):
    """Campaigns page — lists campaigns from all connected channels."""
    project = _get_user_project(request, project_id)
    channels = project.channels.filter(is_active=True)

    context = {
        **_base_context(request),
        "page_title": f"Campanhas — {project.name}",
        "page_id": "project_campaigns",
        "project": project,
        "channels": channels,
    }
    return render(request, "core/project_campaigns.html", context)


@login_required
def project_optimizer(request, project_id: int):
    """Optimizer hub — list channels with optimizer status, click to manage."""
    project = _get_user_project(request, project_id)
    channels = project.channels.filter(is_active=True).select_related("optimizer_config")
    channel_data = []
    for ch in channels:
        config = getattr(ch, "optimizer_config", None)
        channel_data.append({
            "channel": ch,
            "enabled": config.enabled if config else False,
            "mode": config.mode if config else "monitor",
        })
    context = {
        **_base_context(request),
        "page_title": f"Optimizer — {project.name}",
        "page_id": "project_optimizer",
        "project": project,
        "channel_data": channel_data,
    }
    return render(request, "core/project_optimizer.html", context)


@login_required
def project_settings(request, project_id: int):
    """Project settings — edit name, description, danger zone."""
    project = _get_user_project(request, project_id)

    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "delete":
            name = project.name
            project.delete()
            messages.success(request, f"Projeto '{name}' removido.")
            return redirect("core:dashboard")
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Projeto '{project.name}' atualizado!")
            return redirect("core:project_settings", project_id=project.pk)
    else:
        form = ProjectForm(instance=project)

    context = {
        **_base_context(request),
        "page_title": f"Configurações — {project.name}",
        "page_id": "project_settings",
        "project": project,
        "form": form,
    }
    return render(request, "core/project_settings.html", context)


# ── API Endpoints (HTMX partials) ─────────────────────

@login_required
def api_organic_data(request, project_id: int):
    """Return HTML partial with organic metrics (GA4 + GSC) for HTMX."""
    from datetime import timedelta as _td

    project = _get_user_project(request, project_id)
    sites = project.sites.filter(is_active=True)
    days = _parse_days(request, 7)

    organic_data = {
        "sessions": 0, "sessions_prev": 0, "top_queries": [], "top_pages": [],
        "gsc_clicks": 0, "gsc_impressions": 0, "gsc_ctr": 0, "gsc_position": 0,
        "gsc_clicks_prev": 0, "gsc_impressions_prev": 0,
        "daily": [], "error": "", "days": days, "fetched_at": "",
    }

    # Build a full date range so the chart always covers the requested period
    today = timezone.now().date()
    date_range = [(today - _td(days=days - 1 - i)).isoformat() for i in range(days)]
    daily_map: dict[str, dict] = {
        d: {"date": d, "clicks": 0, "impressions": 0, "ctr": 0, "position": 0, "sessions": 0}
        for d in date_range
    }

    # Collect GA4 sessions per day
    ga4_sessions_map: dict[str, int] = {}

    for site in sites:
        if not site.ga4_property_id or not site.google_refresh_token:
            continue
        try:
            from apps.analytics.ga4_report import GA4ReportClient
            ga4 = GA4ReportClient(
                property_id=site.ga4_property_id,
                refresh_token=site.google_refresh_token,
            )
            traffic = ga4.get_organic_traffic(days=days)
            traffic_prev = ga4.get_organic_traffic(days=days * 2)

            sessions = sum(int(r.get("sessions", 0)) for r in traffic)
            sessions_total = sum(int(r.get("sessions", 0)) for r in traffic_prev)
            sessions_prev = sessions_total - sessions

            organic_data["sessions"] += sessions
            organic_data["sessions_prev"] += sessions_prev

            # Merge GA4 daily sessions into map
            for row in traffic:
                d = row.get("date", "")
                if d:
                    # GA4 can return dates as YYYYMMDD — normalize to YYYY-MM-DD
                    if len(d) == 8 and "-" not in d:
                        d = f"{d[:4]}-{d[4:6]}-{d[6:]}"
                    ga4_sessions_map[d] = ga4_sessions_map.get(d, 0) + int(row.get("sessions", 0))
        except Exception as e:
            logger.warning("GA4 error for site %s: %s", site.pk, e)
            organic_data["error"] = str(e)

        if site.gsc_site_url:
            try:
                from apps.analytics.search_console import SearchConsoleClient
                gsc = SearchConsoleClient(
                    site_url=site.gsc_site_url,
                    refresh_token=site.google_refresh_token,
                )
                daily = gsc.fetch_daily_totals(days=days)
                daily_prev = gsc.fetch_daily_totals(days=days * 2)
                queries = gsc.fetch_queries(days=days, row_limit=5)
                pages = gsc.fetch_pages(days=days, row_limit=5)

                clicks = sum(r.get("clicks", 0) for r in daily)
                impressions = sum(r.get("impressions", 0) for r in daily)
                clicks_total = sum(r.get("clicks", 0) for r in daily_prev)
                impressions_total = sum(r.get("impressions", 0) for r in daily_prev)

                organic_data["gsc_clicks"] += clicks
                organic_data["gsc_impressions"] += impressions
                organic_data["gsc_clicks_prev"] += clicks_total - clicks
                organic_data["gsc_impressions_prev"] += impressions_total - impressions
                if daily:
                    organic_data["gsc_ctr"] = round(sum(r.get("ctr", 0) for r in daily) / len(daily), 2)
                    organic_data["gsc_position"] = round(sum(r.get("position", 0) for r in daily) / len(daily), 1)
                organic_data["top_queries"] = queries[:5]
                organic_data["top_pages"] = pages[:5]

                # Merge GSC daily into the full-range map
                for row in daily:
                    d = row.get("date", "")
                    if d in daily_map:
                        daily_map[d]["clicks"] += row.get("clicks", 0)
                        daily_map[d]["impressions"] += row.get("impressions", 0)
                        daily_map[d]["ctr"] = row.get("ctr", 0)
                        daily_map[d]["position"] = row.get("position", 0)
            except Exception as e:
                logger.warning("GSC error for site %s: %s", site.pk, e)

    # Inject GA4 sessions into the daily entries
    for d, sess in ga4_sessions_map.items():
        if d in daily_map:
            daily_map[d]["sessions"] = sess

    # Sort by date and return complete range
    organic_data["daily"] = sorted(daily_map.values(), key=lambda x: x["date"])

    organic_data["fetched_at"] = timezone.now().strftime("%H:%M")
    return render(request, "partials/organic_card.html", {"data": organic_data, "project": project})


@login_required
def api_ads_data(request, project_id: int):
    """Return HTML partial with Google Ads metrics for HTMX."""
    project = _get_user_project(request, project_id)
    channel = project.channels.filter(platform="google_ads", is_active=True).first()
    days = _parse_days(request, 7)

    ads_data = {"spend": 0, "impressions": 0, "clicks": 0, "conversions": 0,
                "ctr": 0, "cpc": 0, "campaigns_active": 0, "campaigns_paused": 0,
                "spend_prev": 0, "clicks_prev": 0,
                "daily": [], "error": "", "connected": False, "days": days, "fetched_at": ""}

    if channel and channel.is_configured:
        ads_data["connected"] = True
        try:
            from django.conf import settings as s
            from apps.analytics.ads_client import GoogleAdsManager
            cred = channel.credentials
            mgr = GoogleAdsManager(
                client_id=cred.client_id or s.GOOGLE_ADS_CLIENT_ID,
                client_secret=cred.client_secret or s.GOOGLE_ADS_CLIENT_SECRET,
                developer_token=cred.developer_token or getattr(s, "GOOGLE_ADS_DEVELOPER_TOKEN", ""),
                refresh_token=cred.refresh_token,
                customer_id=cred.customer_id.replace("-", ""),
                login_customer_id=(cred.login_customer_id or "").replace("-", ""),
            )
            # Current period
            perf = mgr.get_campaign_performance(days=days)
            if perf.get("success"):
                # Aggregate by date for daily chart
                daily_map = {}
                for row in perf.get("data", []):
                    ads_data["spend"] += row.get("cost_brl", 0)
                    ads_data["impressions"] += row.get("impressions", 0)
                    ads_data["clicks"] += row.get("clicks", 0)
                    ads_data["conversions"] += row.get("conversions", 0)
                    d = row.get("date", "")
                    if d:
                        if d not in daily_map:
                            daily_map[d] = {"date": d, "spend": 0, "clicks": 0, "impressions": 0}
                        daily_map[d]["spend"] += row.get("cost_brl", 0)
                        daily_map[d]["clicks"] += row.get("clicks", 0)
                        daily_map[d]["impressions"] += row.get("impressions", 0)
                ads_data["daily"] = sorted(daily_map.values(), key=lambda x: x["date"])
                if ads_data["impressions"] > 0:
                    ads_data["ctr"] = round(ads_data["clicks"] / ads_data["impressions"] * 100, 2)
                if ads_data["clicks"] > 0:
                    ads_data["cpc"] = round(ads_data["spend"] / ads_data["clicks"], 2)

            # Previous period for comparison
            prev_days = {7: 14, 14: 30, 30: 30}.get(days, 30)
            perf_prev = mgr.get_campaign_performance(days=prev_days)
            if perf_prev.get("success"):
                for row in perf_prev.get("data", []):
                    ads_data["spend_prev"] += row.get("cost_brl", 0)
                    ads_data["clicks_prev"] += row.get("clicks", 0)
                ads_data["spend_prev"] -= ads_data["spend"]
                ads_data["clicks_prev"] -= ads_data["clicks"]

            campaigns = mgr.list_campaigns()
            if campaigns.get("success"):
                for c in campaigns.get("campaigns", []):
                    if c.get("status") == "ENABLED":
                        ads_data["campaigns_active"] += 1
                    else:
                        ads_data["campaigns_paused"] += 1
        except Exception as e:
            logger.warning("Google Ads error: %s", e)
            ads_data["error"] = str(e)

    ads_data["fetched_at"] = timezone.now().strftime("%H:%M")
    return render(request, "partials/ads_card.html", {"data": ads_data, "project": project})


@login_required
def api_meta_data(request, project_id: int):
    """Return HTML partial with Meta Ads metrics for HTMX."""
    project = _get_user_project(request, project_id)
    channel = project.channels.filter(platform="meta_ads", is_active=True).first()
    days = _parse_days(request, 7)

    meta_data = {"spend": 0, "impressions": 0, "clicks": 0, "reach": 0,
                 "ctr": 0, "cpc": 0, "cpm": 0, "campaigns_active": 0,
                 "spend_prev": 0, "clicks_prev": 0,
                 "error": "", "connected": False, "days": days, "fetched_at": ""}

    if channel and channel.is_configured:
        meta_data["connected"] = True
        try:
            from apps.analytics.meta_ads_client import MetaAdsManager
            cred = channel.credentials
            mgr = MetaAdsManager(
                access_token=cred.access_token,
                account_id=cred.account_id,
            )
            # Current period
            insights = mgr.get_campaign_insights(days=days)
            if insights.get("success"):
                for row in insights.get("insights", []):
                    meta_data["spend"] += row.get("spend", 0)
                    meta_data["impressions"] += row.get("impressions", 0)
                    meta_data["clicks"] += row.get("clicks", 0)
                    meta_data["reach"] += row.get("reach", 0)
                if meta_data["impressions"] > 0:
                    meta_data["ctr"] = round(meta_data["clicks"] / meta_data["impressions"] * 100, 2)
                if meta_data["clicks"] > 0:
                    meta_data["cpc"] = round(meta_data["spend"] / meta_data["clicks"], 2)
                if meta_data["impressions"] > 0:
                    meta_data["cpm"] = round(meta_data["spend"] / meta_data["impressions"] * 1000, 2)

            # Previous period for comparison
            prev_days = days * 2
            insights_prev = mgr.get_campaign_insights(days=prev_days)
            if insights_prev.get("success"):
                for row in insights_prev.get("insights", []):
                    meta_data["spend_prev"] += row.get("spend", 0)
                    meta_data["clicks_prev"] += row.get("clicks", 0)
                meta_data["spend_prev"] -= meta_data["spend"]
                meta_data["clicks_prev"] -= meta_data["clicks"]

            campaigns = mgr.list_campaigns()
            if campaigns.get("success"):
                for c in campaigns.get("campaigns", []):
                    if c.get("status") == "ACTIVE":
                        meta_data["campaigns_active"] += 1
        except Exception as e:
            logger.warning("Meta Ads error: %s", e)
            meta_data["error"] = str(e)

    meta_data["fetched_at"] = timezone.now().strftime("%H:%M")
    return render(request, "partials/meta_card.html", {"data": meta_data, "project": project})


@login_required
def api_campaigns_google(request, project_id: int):
    """Return HTML partial with per-campaign Google Ads table for HTMX."""
    project = _get_user_project(request, project_id)
    channel = project.channels.filter(platform="google_ads", is_active=True).first()
    days = _parse_days(request, 7)
    sort = request.GET.get("sort", "spend")
    order = request.GET.get("order", "desc")
    q = request.GET.get("q", "").strip()

    ctx = {"campaigns": [], "error": "", "connected": False, "days": days,
           "sort": sort, "order": order, "q": q, "project": project}

    if not channel or not channel.is_configured:
        return render(request, "partials/campaigns_google_table.html", {"data": ctx, "project": project})

    ctx["connected"] = True
    try:
        from django.conf import settings as s
        from apps.analytics.ads_client import GoogleAdsManager
        cred = channel.credentials
        mgr = GoogleAdsManager(
            client_id=cred.client_id or s.GOOGLE_ADS_CLIENT_ID,
            client_secret=cred.client_secret or s.GOOGLE_ADS_CLIENT_SECRET,
            developer_token=cred.developer_token or getattr(s, "GOOGLE_ADS_DEVELOPER_TOKEN", ""),
            refresh_token=cred.refresh_token,
            customer_id=cred.customer_id.replace("-", ""),
            login_customer_id=(cred.login_customer_id or "").replace("-", ""),
        )
        perf = mgr.get_campaign_performance(days=days)
        if perf.get("success"):
            camp_map = {}
            for row in perf.get("data", []):
                cid = row.get("campaign_id", "")
                if cid not in camp_map:
                    camp_map[cid] = {
                        "id": cid, "name": row.get("campaign_name", ""),
                        "spend": 0, "impressions": 0, "clicks": 0,
                        "conversions": 0, "ctr": 0, "cpc": 0,
                    }
                camp_map[cid]["spend"] += row.get("cost_brl", 0)
                camp_map[cid]["impressions"] += row.get("impressions", 0)
                camp_map[cid]["clicks"] += row.get("clicks", 0)
                camp_map[cid]["conversions"] += row.get("conversions", 0)

            # Compute CTR/CPC per campaign
            for c in camp_map.values():
                if c["impressions"] > 0:
                    c["ctr"] = round(c["clicks"] / c["impressions"] * 100, 2)
                if c["clicks"] > 0:
                    c["cpc"] = round(c["spend"] / c["clicks"], 2)

            campaigns_list = list(camp_map.values())

            # Enrich with status from list_campaigns
            list_res = mgr.list_campaigns()
            if list_res.get("success"):
                status_map = {c["id"]: c for c in list_res["campaigns"]}
                for c in campaigns_list:
                    info = status_map.get(c["id"], {})
                    c["status"] = info.get("status", "UNKNOWN")
                    c["daily_budget"] = info.get("daily_budget_brl", 0)
                    c["channel_type"] = info.get("channel_type", "")

            # Filter by search query
            if q:
                campaigns_list = [c for c in campaigns_list if q.lower() in c["name"].lower()]

            # Sort
            reverse = order == "desc"
            campaigns_list.sort(key=lambda x: x.get(sort, 0) if isinstance(x.get(sort, 0), (int, float)) else str(x.get(sort, "")), reverse=reverse)

            ctx["campaigns"] = campaigns_list
    except Exception as e:
        logger.warning("Google Ads campaigns error: %s", e)
        ctx["error"] = str(e)

    return render(request, "partials/campaigns_google_table.html", {"data": ctx, "project": project})


@login_required
def api_campaigns_meta(request, project_id: int):
    """Return HTML partial with per-campaign Meta Ads table for HTMX."""
    project = _get_user_project(request, project_id)
    channel = project.channels.filter(platform="meta_ads", is_active=True).first()
    days = _parse_days(request, 7)
    sort = request.GET.get("sort", "spend")
    order = request.GET.get("order", "desc")
    q = request.GET.get("q", "").strip()

    ctx = {"campaigns": [], "error": "", "connected": False, "days": days,
           "sort": sort, "order": order, "q": q, "project": project}

    if not channel or not channel.is_configured:
        return render(request, "partials/campaigns_meta_table.html", {"data": ctx, "project": project})

    ctx["connected"] = True
    try:
        from apps.analytics.meta_ads_client import MetaAdsManager
        cred = channel.credentials
        mgr = MetaAdsManager(
            access_token=cred.access_token,
            account_id=cred.account_id,
        )
        insights = mgr.get_campaign_insights(days=days)
        if insights.get("success"):
            campaigns_list = []
            for row in insights.get("insights", []):
                campaigns_list.append({
                    "id": row.get("campaign_id", ""),
                    "name": row.get("campaign_name", ""),
                    "spend": row.get("spend", 0),
                    "impressions": row.get("impressions", 0),
                    "clicks": row.get("clicks", 0),
                    "reach": row.get("reach", 0),
                    "ctr": row.get("ctr", 0) or 0,
                    "cpc": row.get("cpc", 0) or 0,
                    "cpm": row.get("cpm", 0) or 0,
                })

            # Enrich with status/objective from list_campaigns
            list_res = mgr.list_campaigns()
            if list_res.get("success"):
                status_map = {c["id"]: c for c in list_res["campaigns"]}
                for c in campaigns_list:
                    info = status_map.get(c["id"], {})
                    c["status"] = info.get("status", "UNKNOWN")
                    c["objective"] = info.get("objective", "")
                    c["daily_budget"] = info.get("daily_budget")

            if q:
                campaigns_list = [c for c in campaigns_list if q.lower() in c["name"].lower()]

            reverse = order == "desc"
            campaigns_list.sort(key=lambda x: x.get(sort, 0) if isinstance(x.get(sort, 0), (int, float)) else str(x.get(sort, "")), reverse=reverse)

            ctx["campaigns"] = campaigns_list
    except Exception as e:
        logger.warning("Meta Ads campaigns error: %s", e)
        ctx["error"] = str(e)

    return render(request, "partials/campaigns_meta_table.html", {"data": ctx, "project": project})


@login_required
def api_campaign_ad_groups(request, project_id: int, campaign_id: str):
    """Return HTML partial with ad groups for a Google Ads campaign (HTMX)."""
    project = _get_user_project(request, project_id)
    channel = project.channels.filter(platform="google_ads", is_active=True).first()

    ctx = {"ad_groups": [], "error": "", "campaign_id": campaign_id}

    if not channel or not channel.is_configured:
        return render(request, "partials/campaign_ad_groups.html", {"data": ctx, "project": project})

    try:
        from django.conf import settings as s
        from apps.analytics.ads_client import GoogleAdsManager
        cred = channel.credentials
        mgr = GoogleAdsManager(
            client_id=cred.client_id or s.GOOGLE_ADS_CLIENT_ID,
            client_secret=cred.client_secret or s.GOOGLE_ADS_CLIENT_SECRET,
            developer_token=cred.developer_token or getattr(s, "GOOGLE_ADS_DEVELOPER_TOKEN", ""),
            refresh_token=cred.refresh_token,
            customer_id=cred.customer_id.replace("-", ""),
            login_customer_id=(cred.login_customer_id or "").replace("-", ""),
        )
        result = mgr.list_ad_groups(campaign_id)
        if result.get("success"):
            ad_groups = result.get("ad_groups", [])
            for ag in ad_groups:
                if ag.get("clicks", 0) > 0:
                    ag["ctr"] = round(ag["clicks"] / ag.get("impressions", 1) * 100, 2)
                    ag["cpc"] = round(ag.get("cost_brl", 0) / ag["clicks"], 2)
                else:
                    ag["ctr"] = 0
                    ag["cpc"] = 0
            ctx["ad_groups"] = ad_groups
    except Exception as e:
        logger.warning("Google Ads ad groups error: %s", e)
        ctx["error"] = str(e)

    return render(request, "partials/campaign_ad_groups.html", {"data": ctx, "project": project})


@login_required
def api_ad_group_ads(request, project_id: int, ad_group_id: str):
    """Return HTML partial with ads for a Google Ads ad group (HTMX)."""
    project = _get_user_project(request, project_id)
    channel = project.channels.filter(platform="google_ads", is_active=True).first()

    ctx = {"ads": [], "error": "", "ad_group_id": ad_group_id}

    if not channel or not channel.is_configured:
        return render(request, "partials/ad_group_ads.html", {"data": ctx, "project": project})

    try:
        from django.conf import settings as s
        from apps.analytics.ads_client import GoogleAdsManager
        cred = channel.credentials
        mgr = GoogleAdsManager(
            client_id=cred.client_id or s.GOOGLE_ADS_CLIENT_ID,
            client_secret=cred.client_secret or s.GOOGLE_ADS_CLIENT_SECRET,
            developer_token=cred.developer_token or getattr(s, "GOOGLE_ADS_DEVELOPER_TOKEN", ""),
            refresh_token=cred.refresh_token,
            customer_id=cred.customer_id.replace("-", ""),
            login_customer_id=(cred.login_customer_id or "").replace("-", ""),
        )
        result = mgr.list_ads(ad_group_id)
        if result.get("success"):
            ads = result.get("ads", [])
            for ad in ads:
                if ad.get("clicks", 0) > 0:
                    ad["ctr"] = round(ad["clicks"] / ad.get("impressions", 1) * 100, 2)
                    ad["cpc"] = round(ad.get("cost_brl", 0) / ad["clicks"], 2)
                else:
                    ad["ctr"] = 0
                    ad["cpc"] = 0
            ctx["ads"] = ads
        else:
            ctx["error"] = result.get("error", "Erro desconhecido")
    except Exception as e:
        logger.warning("Google Ads ads error: %s", e)
        ctx["error"] = str(e)

    return render(request, "partials/ad_group_ads.html", {"data": ctx, "project": project})


@login_required
@require_POST
def api_campaign_update_budget(request, project_id: int):
    """Update campaign budget inline (JSON)."""
    project = _get_user_project(request, project_id)
    channel = project.channels.filter(platform="google_ads", is_active=True).first()

    if not channel or not channel.is_configured:
        return JsonResponse({"success": False, "error": "Canal não configurado"})

    try:
        body = json.loads(request.body)
        campaign_id = body.get("campaign_id", "")
        new_budget = float(body.get("daily_budget_brl", 0))
        if new_budget <= 0:
            return JsonResponse({"success": False, "error": "Budget deve ser maior que zero"})

        from django.conf import settings as s
        from apps.analytics.ads_client import GoogleAdsManager
        cred = channel.credentials
        mgr = GoogleAdsManager(
            client_id=cred.client_id or s.GOOGLE_ADS_CLIENT_ID,
            client_secret=cred.client_secret or s.GOOGLE_ADS_CLIENT_SECRET,
            developer_token=cred.developer_token or getattr(s, "GOOGLE_ADS_DEVELOPER_TOKEN", ""),
            refresh_token=cred.refresh_token,
            customer_id=cred.customer_id.replace("-", ""),
            login_customer_id=(cred.login_customer_id or "").replace("-", ""),
        )
        result = mgr.update_campaign_budget_amount(
            campaign_id=campaign_id,
            new_daily_budget_brl=new_budget,
        )
        return JsonResponse(result)
    except Exception as e:
        logger.warning("Update budget error: %s", e)
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def api_campaign_ad_sets_meta(request, project_id: int, campaign_id: str):
    """Return HTML partial with ad sets for a Meta Ads campaign (HTMX)."""
    project = _get_user_project(request, project_id)
    channel = project.channels.filter(platform="meta_ads", is_active=True).first()
    days = _parse_days(request, 7)

    ctx = {"ad_sets": [], "error": "", "campaign_id": campaign_id}

    if not channel or not channel.is_configured:
        return render(request, "partials/campaign_ad_sets_meta.html", {"data": ctx, "project": project})

    try:
        from apps.analytics.meta_ads_client import MetaAdsManager
        cred = channel.credentials
        mgr = MetaAdsManager(
            access_token=cred.access_token,
            account_id=cred.account_id,
        )
        result = mgr.list_ad_sets(campaign_id=campaign_id)
        if result.get("success"):
            ad_sets = result.get("ad_sets", [])
            # Enrich with insights (metrics)
            for adset in ad_sets:
                ins = mgr.get_ad_set_insights(adset["id"], days=days)
                if ins.get("success") and ins.get("insights"):
                    row = ins["insights"][0]
                    adset["spend"] = row.get("spend", 0)
                    adset["impressions"] = row.get("impressions", 0)
                    adset["clicks"] = row.get("clicks", 0)
                    adset["reach"] = row.get("reach", 0)
                    adset["ctr"] = row.get("ctr", 0) or 0
                    adset["cpc"] = row.get("cpc", 0) or 0
                else:
                    adset.update({"spend": 0, "impressions": 0, "clicks": 0, "reach": 0, "ctr": 0, "cpc": 0})
            ctx["ad_sets"] = ad_sets
    except Exception as e:
        logger.warning("Meta Ads ad sets error: %s", e)
        ctx["error"] = str(e)

    return render(request, "partials/campaign_ad_sets_meta.html", {"data": ctx, "project": project})


@login_required
@require_POST
def api_campaign_update_budget_meta(request, project_id: int):
    """Update Meta Ads campaign budget inline (JSON)."""
    project = _get_user_project(request, project_id)
    channel = project.channels.filter(platform="meta_ads", is_active=True).first()

    if not channel or not channel.is_configured:
        return JsonResponse({"success": False, "error": "Canal Meta Ads não configurado"})

    try:
        body = json.loads(request.body)
        campaign_id = body.get("campaign_id", "")
        new_budget = float(body.get("daily_budget_brl", 0))
        if new_budget <= 0:
            return JsonResponse({"success": False, "error": "Budget deve ser maior que zero"})

        from apps.analytics.meta_ads_client import MetaAdsManager
        cred = channel.credentials
        mgr = MetaAdsManager(
            access_token=cred.access_token,
            account_id=cred.account_id,
        )
        result = mgr.update_campaign(campaign_id, daily_budget=new_budget)
        return JsonResponse(result)
    except Exception as e:
        logger.warning("Update Meta budget error: %s", e)
        return JsonResponse({"success": False, "error": str(e)})


# ── Phase 3: Alerts & Reports ────────────────────────────────────


@login_required
def project_alerts(request, project_id: int):
    """Alert rules management page."""
    project = _get_user_project(request, project_id)
    from .models import AlertRule, AlertEvent
    rules = project.alert_rules.all()
    recent_events = AlertEvent.objects.filter(rule__project=project).order_by("-triggered_at")[:20]
    unread_count = AlertEvent.objects.filter(rule__project=project, is_read=False).count()

    context = {
        **_base_context(request),
        "page_title": f"Alertas — {project.name}",
        "page_id": "project_alerts",
        "project": project,
        "rules": rules,
        "recent_events": recent_events,
        "unread_count": unread_count,
    }
    return render(request, "core/project_alerts.html", context)


@login_required
def alert_add(request, project_id: int):
    """Create a new alert rule."""
    project = _get_user_project(request, project_id)
    from .models import AlertRule

    if request.method == "POST":
        AlertRule.objects.create(
            project=project,
            name=request.POST.get("name", "").strip(),
            metric=request.POST.get("metric", "sessions"),
            condition=request.POST.get("condition", "gt"),
            threshold=request.POST.get("threshold", 0),
            notify_email=request.POST.get("notify_email") == "on",
        )
        messages.success(request, "Alerta criado com sucesso!")
        return redirect("core:project_alerts", project_id=project.id)

    context = {
        **_base_context(request),
        "page_title": "Novo Alerta",
        "project": project,
        "metric_choices": AlertRule.METRIC_CHOICES,
        "condition_choices": AlertRule.CONDITION_CHOICES,
    }
    return render(request, "core/alert_form.html", context)


@login_required
def alert_edit(request, project_id: int, alert_id: int):
    """Edit an existing alert rule."""
    project = _get_user_project(request, project_id)
    from .models import AlertRule
    rule = get_object_or_404(AlertRule, pk=alert_id, project=project)

    if request.method == "POST":
        rule.name = request.POST.get("name", "").strip()
        rule.metric = request.POST.get("metric", rule.metric)
        rule.condition = request.POST.get("condition", rule.condition)
        rule.threshold = request.POST.get("threshold", rule.threshold)
        rule.notify_email = request.POST.get("notify_email") == "on"
        rule.is_active = request.POST.get("is_active") == "on"
        rule.save()
        messages.success(request, "Alerta atualizado!")
        return redirect("core:project_alerts", project_id=project.id)

    context = {
        **_base_context(request),
        "page_title": f"Editar Alerta — {rule.name}",
        "project": project,
        "rule": rule,
        "metric_choices": AlertRule.METRIC_CHOICES,
        "condition_choices": AlertRule.CONDITION_CHOICES,
    }
    return render(request, "core/alert_form.html", context)


@login_required
@require_POST
def alert_delete(request, project_id: int, alert_id: int):
    """Delete an alert rule."""
    project = _get_user_project(request, project_id)
    from .models import AlertRule
    rule = get_object_or_404(AlertRule, pk=alert_id, project=project)
    rule.delete()
    messages.success(request, "Alerta removido.")
    return redirect("core:project_alerts", project_id=project.id)


@login_required
@require_POST
def alert_mark_read(request, project_id: int):
    """Mark all alert events as read."""
    project = _get_user_project(request, project_id)
    from .models import AlertEvent
    AlertEvent.objects.filter(rule__project=project, is_read=False).update(is_read=True)
    messages.success(request, "Alertas marcados como lidos.")
    return redirect("core:project_alerts", project_id=project.id)


@login_required
def api_alert_events(request, project_id: int):
    """HTMX partial — recent alert events list."""
    project = _get_user_project(request, project_id)
    from .models import AlertEvent
    events = AlertEvent.objects.filter(rule__project=project).order_by("-triggered_at")[:30]
    return render(request, "partials/alert_events.html", {"events": events, "project": project})


@login_required
def export_campaigns_csv(request, project_id: int):
    """Export campaign data as CSV."""
    project = _get_user_project(request, project_id)
    days = _parse_days(request, 7)
    platform = request.GET.get("platform", "google_ads")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="campaigns_{project.slug}_{platform}_{days}d.csv"'
    writer = csv.writer(response)

    if platform == "google_ads":
        channel = project.channels.filter(platform="google_ads", is_active=True).first()
        writer.writerow(["Campanha", "Status", "Gasto (R$)", "Impressões", "Cliques", "CTR (%)", "CPC (R$)", "Conversões"])
        if channel and channel.is_configured:
            try:
                from django.conf import settings as s
                from apps.analytics.ads_client import GoogleAdsManager
                cred = channel.credentials
                mgr = GoogleAdsManager(
                    client_id=cred.client_id or s.GOOGLE_ADS_CLIENT_ID,
                    client_secret=cred.client_secret or s.GOOGLE_ADS_CLIENT_SECRET,
                    developer_token=cred.developer_token or getattr(s, "GOOGLE_ADS_DEVELOPER_TOKEN", ""),
                    refresh_token=cred.refresh_token,
                    customer_id=cred.customer_id.replace("-", ""),
                    login_customer_id=(cred.login_customer_id or "").replace("-", ""),
                )
                perf = mgr.get_campaign_performance(days=days)
                camp_map = {}
                if perf.get("success"):
                    for row in perf.get("data", []):
                        cid = row.get("campaign_id", "")
                        if cid not in camp_map:
                            camp_map[cid] = {"name": row.get("campaign_name", ""), "spend": 0, "impressions": 0, "clicks": 0, "conversions": 0}
                        camp_map[cid]["spend"] += row.get("cost_brl", 0)
                        camp_map[cid]["impressions"] += row.get("impressions", 0)
                        camp_map[cid]["clicks"] += row.get("clicks", 0)
                        camp_map[cid]["conversions"] += row.get("conversions", 0)

                list_res = mgr.list_campaigns()
                status_map = {}
                if list_res.get("success"):
                    status_map = {c["id"]: c.get("status", "") for c in list_res["campaigns"]}

                for cid, c in camp_map.items():
                    ctr = round(c["clicks"] / c["impressions"] * 100, 2) if c["impressions"] > 0 else 0
                    cpc = round(c["spend"] / c["clicks"], 2) if c["clicks"] > 0 else 0
                    writer.writerow([c["name"], status_map.get(cid, ""), f'{c["spend"]:.2f}', c["impressions"], c["clicks"], ctr, f'{cpc:.2f}', c["conversions"]])
            except Exception as e:
                writer.writerow([f"Erro: {e}"])
    else:
        channel = project.channels.filter(platform="meta_ads", is_active=True).first()
        writer.writerow(["Campanha", "Status", "Gasto (R$)", "Alcance", "Impressões", "Cliques", "CTR (%)", "CPC (R$)"])
        if channel and channel.is_configured:
            try:
                from apps.analytics.meta_ads_client import MetaAdsManager
                cred = channel.credentials
                mgr = MetaAdsManager(access_token=cred.access_token, account_id=cred.account_id)
                insights = mgr.get_campaign_insights(days=days)
                list_res = mgr.list_campaigns()
                status_map = {}
                if list_res.get("success"):
                    status_map = {c["id"]: c.get("status", "") for c in list_res["campaigns"]}

                if insights.get("success"):
                    for row in insights.get("insights", []):
                        writer.writerow([
                            row.get("campaign_name", ""),
                            status_map.get(row.get("campaign_id", ""), ""),
                            f'{row.get("spend", 0):.2f}',
                            row.get("reach", 0),
                            row.get("impressions", 0),
                            row.get("clicks", 0),
                            f'{(row.get("ctr") or 0):.2f}',
                            f'{(row.get("cpc") or 0):.2f}',
                        ])
            except Exception as e:
                writer.writerow([f"Erro: {e}"])

    return response


@login_required
def export_report_html(request, project_id: int):
    """Print-friendly HTML report for browser PDF export (Ctrl+P)."""
    project = _get_user_project(request, project_id)
    days = _parse_days(request, 7)

    context = {
        "project": project,
        "days": days,
        "generated_at": timezone.now(),
    }
    return render(request, "core/report_print.html", context)


# ── Audit Parameters (IA Config) ───────────────────────────────

@login_required
def audit_parameters(request, project_id: int):
    """Parâmetros IA — configure which data sources and dimensions the audit uses."""
    project = _get_user_project(request, project_id)
    from .models import AuditConfig

    config, _created = AuditConfig.objects.get_or_create(project=project)

    if request.method == "POST":
        # Toggle fields from form checkboxes
        toggle_fields = [
            # Sources
            "source_meta_ads", "source_google_ads", "source_seo", "source_ga4",
            # Meta dimensions
            "meta_campaign_structure", "meta_audience_targeting", "meta_creatives",
            "meta_budget_bidding", "meta_placements", "meta_demographics",
            "meta_ad_performance", "meta_conversion_tracking",
            # Google dimensions
            "google_campaign_structure", "google_keywords", "google_search_terms",
            "google_ad_copies", "google_extensions", "google_bidding",
            "google_quality_score", "google_geo_targeting", "google_conversion_tracking",
            # GA4 dimensions
            "ga4_traffic_sources", "ga4_top_pages", "ga4_conversions",
            "ga4_demographics", "ga4_devices", "ga4_organic",
            # SEO dimensions
            "seo_top_queries", "seo_top_pages", "seo_indexing",
            # Cross-platform
            "cross_platform_synthesis", "brand_dna_context",
        ]
        for field in toggle_fields:
            setattr(config, field, field in request.POST)

        # Select fields
        config.ai_depth = request.POST.get("ai_depth", "standard")
        config.ai_language = request.POST.get("ai_language", "pt-BR")
        config.save()

        messages.success(request, "Parâmetros de auditoria salvos!")
        return redirect("core:audit_parameters", project_id=project.id)

    context = {
        **_base_context(request),
        "page_title": f"Parâmetros IA — {project.name}",
        "page_id": "audit_parameters",
        "project": project,
        "config": config,
    }
    return render(request, "core/audit_parameters.html", context)


# ── AI Audit ────────────────────────────────────────────────────

@login_required
def project_audit(request, project_id: int):
    """AI Audit page — show latest report or let user trigger a new audit."""
    project = _get_user_project(request, project_id)
    from .models import AuditReport, BrandProfile, DataSnapshot, ProjectScore

    reports = AuditReport.objects.filter(project=project).order_by("-created_at")[:10]
    latest = reports.first() if reports.exists() else None

    # Load latest report recommendations
    recommendations = []
    if latest and latest.status == "done":
        recommendations = latest.recommendations.all()

    # Brand profile (if exists)
    brand_profile = BrandProfile.objects.filter(project=project).first()

    # Gamification score
    project_score = ProjectScore.objects.filter(project=project).first()

    # Data cache freshness
    cache_status = {}
    for snap in DataSnapshot.objects.filter(project=project, is_valid=True).order_by("-collected_at")[:30]:
        if snap.data_type not in cache_status:
            cache_status[snap.data_type] = {
                "age": snap.age_display,
                "expired": snap.is_expired,
                "count": snap.record_count,
            }

    context = {
        **_base_context(request),
        "page_title": f"Auditoria — {project.name}",
        "page_id": "project_audit",
        "project": project,
        "reports": reports,
        "latest": latest,
        "recommendations": recommendations,
        "rec_pending": [r for r in recommendations if r.status == "pending"],
        "rec_applied": [r for r in recommendations if r.status == "applied"],
        "rec_dismissed": [r for r in recommendations if r.status == "dismissed"],
        "brand_profile": brand_profile,
        "cache_status": cache_status,
        "project_score": project_score,
    }
    return render(request, "core/project_audit.html", context)


@login_required
@require_POST
def audit_run(request, project_id: int):
    """Trigger a new AI audit — always runs in background thread."""
    import threading
    project = _get_user_project(request, project_id)

    def _run_in_background(pid):
        """Run audit in a separate thread to avoid Gunicorn timeout."""
        import django
        from django.db import connection
        connection.close()  # Each thread needs its own DB connection
        try:
            from .audit_engine import run_audit
            run_audit(pid)
        except Exception as exc:
            logger.error("Background audit failed for project %d: %s", pid, exc)

    thread = threading.Thread(target=_run_in_background, args=(project.id,), daemon=True)
    thread.start()

    messages.info(request, "Auditoria iniciada! Acompanhe o progresso abaixo.")
    return redirect("core:project_audit", project_id=project.id)


@login_required
@require_POST
def brand_intel_refresh(request, project_id: int):
    """Trigger a brand intelligence refresh in the background."""
    import threading
    project = _get_user_project(request, project_id)

    def _refresh_bg(pid):
        from django.db import connection
        connection.close()
        try:
            from .audit_engine import refresh_brand_intelligence
            refresh_brand_intelligence(pid)
        except Exception as exc:
            logger.error("Brand intel refresh failed for project %d: %s", pid, exc)

    thread = threading.Thread(target=_refresh_bg, args=(project.id,), daemon=True)
    thread.start()

    messages.info(request, "Inteligência da marca sendo atualizada! Pode levar alguns segundos.")
    return redirect("core:project_audit", project_id=project.id)


@login_required
def audit_status(request, project_id: int):
    """HTMX endpoint: returns audit progress HTML fragment."""
    project = _get_user_project(request, project_id)
    from .models import AuditReport

    latest = AuditReport.objects.filter(project=project).order_by("-created_at").first()

    if not latest:
        return JsonResponse({"status": "none"})

    # Auto-fix stale running reports (stuck > 5 min)
    if latest.status == "running" and latest.created_at:
        age = (timezone.now() - latest.created_at).total_seconds()
        if age > 300:  # 5 minutes
            latest.status = "error"
            latest.error_message = "Timeout: auditoria demorou mais de 5 minutos."
            latest.duration_seconds = age
            latest.save(update_fields=["status", "error_message", "duration_seconds"])

    STEP_LABELS = {
        "brand_dna": "Analisando Brand DNA...",
        "scanning_website": "Escaneando o site...",
        "scanning_social": "Coletando redes sociais...",
        "generating_brand_dna": "Gerando inteligência da marca...",
        "collecting_google_ads": "Coletando dados Google Ads...",
        "collecting_meta_ads": "Coletando dados Meta Ads...",
        "collecting_seo": "Coletando dados SEO...",
        "ai_analyzing_meta": "IA analisando Meta Ads...",
        "ai_analyzing_google": "IA analisando Google Ads...",
        "ai_analyzing_ga4": "IA analisando GA4 Analytics...",
        "ai_synthesizing": "IA sintetizando análise cross-platform...",
        "ai_analyzing": "IA analisando dados...",
        "collecting_ga4": "Coletando dados GA4 Analytics...",
        "saving_results": "Salvando resultados...",
    }

    step_label = STEP_LABELS.get(latest.progress_step, latest.progress_step or "Iniciando...")

    return JsonResponse({
        "status": latest.status,
        "progress_step": latest.progress_step,
        "step_label": step_label,
        "score": latest.overall_score,
        "duration": latest.duration_seconds,
        "error": latest.error_message[:200] if latest.error_message else "",
    })


@login_required
@require_POST
def audit_apply(request, project_id: int, rec_id: int):
    """Apply a single recommendation."""
    project = _get_user_project(request, project_id)
    from .audit_engine import apply_recommendation
    from .models import AuditRecommendation

    rec = get_object_or_404(AuditRecommendation, id=rec_id, report__project=project)

    result = apply_recommendation(rec.id)

    if result.get("success"):
        messages.success(request, f"✅ Aplicado: {rec.title}")
    else:
        messages.error(request, f"Falha: {result.get('error', 'Erro desconhecido')}")

    return redirect("core:project_audit", project_id=project.id)


@login_required
@require_POST
def audit_apply_all(request, project_id: int):
    """Apply ALL pending auto-applicable recommendations."""
    project = _get_user_project(request, project_id)
    from .audit_engine import apply_recommendation
    from .models import AuditReport

    latest = AuditReport.objects.filter(
        project=project, status="done",
    ).order_by("-created_at").first()

    if not latest:
        messages.error(request, "Nenhum relatório de auditoria disponível.")
        return redirect("core:project_audit", project_id=project.id)

    pending = latest.recommendations.filter(status="pending", can_auto_apply=True)
    applied = 0
    failed = 0

    for rec in pending:
        result = apply_recommendation(rec.id)
        if result.get("success"):
            applied += 1
        else:
            failed += 1

    if applied:
        messages.success(request, f"✅ {applied} recomendações aplicadas com sucesso!")
    if failed:
        messages.warning(request, f"⚠️ {failed} recomendações falharam.")
    if not applied and not failed:
        messages.info(request, "Nenhuma recomendação pendente para aplicar.")

    return redirect("core:project_audit", project_id=project.id)


@login_required
@require_POST
def audit_dismiss(request, project_id: int, rec_id: int):
    """Dismiss a recommendation (mark as ignored)."""
    project = _get_user_project(request, project_id)
    from .models import AuditRecommendation

    rec = get_object_or_404(AuditRecommendation, id=rec_id, report__project=project)
    rec.status = "dismissed"
    rec.save()
    messages.info(request, f"Recomendação descartada: {rec.title}")
    return redirect("core:project_audit", project_id=project.id)


# ── AI Knowledge Base Views ─────────────────────────────────────

@login_required
def ai_knowledge_base(request, project_id: int):
    """AI Knowledge Base — view/edit the accumulated learning context."""
    project = _get_user_project(request, project_id)
    from .models import ProjectLearningContext, RecommendationNote

    ctx, _ = ProjectLearningContext.objects.get_or_create(project=project)

    if request.method == "POST":
        ctx.compiled_prompt = request.POST.get("compiled_prompt", "")
        ctx.general_guidelines = request.POST.get("general_guidelines", "")
        ctx.save()
        messages.success(request, "Base de conhecimento salva!")
        return redirect("core:ai_knowledge_base", project_id=project.id)

    notes = RecommendationNote.objects.filter(
        recommendation__report__project=project,
    ).select_related("recommendation", "user").order_by("-created_at")

    total_notes = notes.count()

    # Simple pagination (20 per page)
    page = int(request.GET.get("page", 1))
    per_page = 20
    start = (page - 1) * per_page
    notes_page = notes[start:start + per_page]
    total_pages = (total_notes + per_page - 1) // per_page if total_notes else 1

    context = {
        **_base_context(request),
        "page_title": f"Base de Conhecimento IA — {project.name}",
        "page_id": "ai_knowledge_base",
        "project": project,
        "learning_ctx": ctx,
        "notes": notes_page,
        "total_notes": total_notes,
        "page": page,
        "total_pages": total_pages,
        "page_range": range(1, total_pages + 1),
    }
    return render(request, "core/ai_knowledge_base.html", context)


@login_required
@require_POST
def knowledge_base_edit_note(request, project_id: int, note_id: int):
    """AJAX: Edit a recommendation note's text."""
    project = _get_user_project(request, project_id)
    from .models import RecommendationNote

    note = get_object_or_404(
        RecommendationNote, id=note_id,
        recommendation__report__project=project,
    )

    data = json.loads(request.body) if request.content_type == "application/json" else request.POST
    new_text = data.get("text", "").strip()
    if not new_text:
        return JsonResponse({"error": "Texto não pode ser vazio."}, status=400)

    note.text = new_text
    note.save()
    return JsonResponse({"success": True, "text": note.text, "updated_at": note.updated_at.isoformat()})


@login_required
@require_POST
def knowledge_base_delete_note(request, project_id: int, note_id: int):
    """AJAX: Delete a recommendation note."""
    project = _get_user_project(request, project_id)
    from .models import RecommendationNote

    note = get_object_or_404(
        RecommendationNote, id=note_id,
        recommendation__report__project=project,
    )
    note.delete()
    return JsonResponse({"success": True})


@login_required
@require_POST
def knowledge_base_recompile(request, project_id: int):
    """AJAX: Recompile the learning context from all notes."""
    project = _get_user_project(request, project_id)
    from .audit_engine import compile_learning_context

    result = compile_learning_context(project)
    return JsonResponse({
        "success": True,
        "compiled_prompt": result["compiled_prompt"],
        "auto_summary": result["auto_summary"],
        "notes_count": result["notes_count"],
    })


# ── Audit AJAX Endpoints ───────────────────────────────────────

@login_required
def audit_preview(request, project_id: int, rec_id: int):
    """AJAX GET: Generate an action preview for a recommendation."""
    project = _get_user_project(request, project_id)
    from .audit_engine import generate_action_preview
    from .models import AuditRecommendation

    get_object_or_404(AuditRecommendation, id=rec_id, report__project=project)
    result = generate_action_preview(rec_id)
    return JsonResponse(result)


@login_required
@require_POST
def audit_apply_ajax(request, project_id: int, rec_id: int):
    """AJAX POST: Apply a recommendation and return JSON."""
    project = _get_user_project(request, project_id)
    from .audit_engine import apply_recommendation
    from .models import AuditRecommendation

    rec = get_object_or_404(AuditRecommendation, id=rec_id, report__project=project)

    # If request includes a generated payload, update the rec first
    if request.content_type == "application/json":
        data = json.loads(request.body)
        if data.get("payload") and data.get("action_type"):
            rec.action_payload = {"action_type": data["action_type"], **data["payload"]}
            rec.can_auto_apply = True
            rec.save()

    result = apply_recommendation(rec.id)
    rec.refresh_from_db()
    return JsonResponse({
        **result,
        "status": rec.status,
        "applied_at": rec.applied_at.isoformat() if rec.applied_at else None,
    })


@login_required
@require_POST
def audit_verify(request, project_id: int, rec_id: int):
    """AJAX POST: Verify a recommendation was actually applied."""
    project = _get_user_project(request, project_id)
    from .audit_engine import verify_recommendation
    from .models import AuditRecommendation

    get_object_or_404(AuditRecommendation, id=rec_id, report__project=project)
    result = verify_recommendation(rec_id)
    return JsonResponse(result)


@login_required
@require_POST
def audit_add_note(request, project_id: int, rec_id: int):
    """AJAX POST: Add a user observation to a recommendation."""
    project = _get_user_project(request, project_id)
    from .models import AuditRecommendation, RecommendationNote

    rec = get_object_or_404(AuditRecommendation, id=rec_id, report__project=project)

    data = json.loads(request.body) if request.content_type == "application/json" else request.POST
    text = data.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "Texto não pode ser vazio."}, status=400)

    note = RecommendationNote.objects.create(
        recommendation=rec,
        user=request.user,
        text=text,
    )
    return JsonResponse({
        "success": True,
        "id": note.id,
        "text": note.text,
        "user_name": request.user.get_full_name() or request.user.username,
        "created_at": note.created_at.isoformat(),
    })


# ── Developer Error Dashboard ────────────────────────────

@login_required
def error_dashboard(request):
    """Staff-only error tracking dashboard — shows SystemErrorLog entries."""
    if not request.user.is_staff:
        return HttpResponseForbidden("Acesso restrito a desenvolvedores.")

    from .models import SystemErrorLog

    # Filters
    error_type = request.GET.get("error_type", "")
    severity = request.GET.get("severity", "")
    resolved = request.GET.get("resolved", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    qs = SystemErrorLog.objects.all()
    if error_type:
        qs = qs.filter(error_type=error_type)
    if severity:
        qs = qs.filter(severity=severity)
    if resolved == "yes":
        qs = qs.filter(resolved=True)
    elif resolved == "no":
        qs = qs.filter(resolved=False)
    if date_from:
        try:
            qs = qs.filter(timestamp__date__gte=date_from)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            qs = qs.filter(timestamp__date__lte=date_to)
        except (ValueError, TypeError):
            pass

    # Stats
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    total_24h = SystemErrorLog.objects.filter(timestamp__gte=last_24h).count()
    unresolved = SystemErrorLog.objects.filter(resolved=False).count()
    most_common = ""
    common_qs = SystemErrorLog.objects.filter(
        timestamp__gte=last_24h,
    ).values("error_type").annotate(count=Sum("id")).order_by("-count").first()
    if common_qs:
        for choice in SystemErrorLog.ERROR_TYPE_CHOICES:
            if choice[0] == common_qs["error_type"]:
                most_common = choice[1]
                break

    # Simple pagination
    page = int(request.GET.get("page", 1))
    per_page = 30
    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    errors = qs[(page - 1) * per_page : page * per_page]

    context = {
        **_base_context(request),
        "page_title": "Error Logs — Developer Dashboard",
        "page_id": "error_dashboard",
        "errors": errors,
        "total": total,
        "total_24h": total_24h,
        "unresolved": unresolved,
        "most_common": most_common,
        "error_type_choices": SystemErrorLog.ERROR_TYPE_CHOICES,
        "severity_choices": SystemErrorLog.SEVERITY_CHOICES,
        # Current filters
        "f_error_type": error_type,
        "f_severity": severity,
        "f_resolved": resolved,
        "f_date_from": date_from,
        "f_date_to": date_to,
        # Pagination
        "page": page,
        "total_pages": total_pages,
        "page_range": range(max(1, page - 3), min(total_pages + 1, page + 4)),
    }
    return render(request, "core/error_dashboard.html", context)


@login_required
@require_POST
def error_resolve(request, error_id: int):
    """Toggle resolved status of an error log entry."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Acesso restrito"}, status=403)

    from .models import SystemErrorLog
    err = get_object_or_404(SystemErrorLog, pk=error_id)
    err.resolved = not err.resolved
    err.save(update_fields=["resolved"])
    return JsonResponse({"success": True, "resolved": err.resolved})


@login_required
@require_POST
def error_update_notes(request, error_id: int):
    """Update developer notes on an error log entry."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Acesso restrito"}, status=403)

    from .models import SystemErrorLog
    err = get_object_or_404(SystemErrorLog, pk=error_id)

    data = json.loads(request.body) if request.content_type == "application/json" else request.POST
    err.developer_notes = data.get("developer_notes", "")
    err.save(update_fields=["developer_notes"])
    return JsonResponse({"success": True})


# ── AI Provider Settings ─────────────────────────────────

@login_required
def ai_settings(request, project_id: int):
    """AI provider configuration page — one API key per provider."""
    from .models import AIProvider
    import json as _json
    project = _get_user_project(request, project_id)

    configured = {p.provider: p for p in AIProvider.objects.filter(project=project)}

    providers_list = []
    for val, label in AIProvider.PROVIDER_CHOICES:
        prov = configured.get(val)
        providers_list.append({
            "key": val,
            "label": label,
            "pk": prov.pk if prov else None,
            "api_key": prov.api_key if prov else "",
            "text_model": prov.text_model if prov else "",
            "image_model": prov.image_model if prov else "",
            "is_default_text": prov.is_default_text if prov else False,
            "is_default_image": prov.is_default_image if prov else False,
        })

    ctx = {
        **_base_context(request),
        "project": project,
        "providers_list": providers_list,
        "providers_json": _json.dumps(providers_list),
        "page_id": "ai_settings",
    }
    return render(request, "core/ai_settings.html", ctx)


@login_required
@require_POST
def ai_provider_save(request, project_id: int):
    """Create or update an AI provider (upsert by project + provider)."""
    from .models import AIProvider
    project = _get_user_project(request, project_id)

    provider = request.POST.get("provider", "").strip()
    api_key = request.POST.get("api_key", "").strip()
    text_model = request.POST.get("text_model", "").strip()
    image_model = request.POST.get("image_model", "").strip()
    is_default_text = request.POST.get("is_default_text") == "on"
    is_default_image = request.POST.get("is_default_image") == "on"

    valid_providers = [c[0] for c in AIProvider.PROVIDER_CHOICES]
    if provider not in valid_providers:
        messages.error(request, "Provedor inválido.")
        return redirect("core:ai_settings", project_id=project.id)

    if not api_key:
        messages.error(request, "API Key é obrigatória.")
        return redirect("core:ai_settings", project_id=project.id)

    prov, created = AIProvider.objects.get_or_create(
        project=project, provider=provider,
        defaults={
            "api_key": api_key,
            "text_model": text_model,
            "image_model": image_model,
            "is_default_text": is_default_text,
            "is_default_image": is_default_image,
        },
    )
    if not created:
        prov.api_key = api_key
        prov.text_model = text_model
        prov.image_model = image_model
        prov.is_default_text = is_default_text
        prov.is_default_image = is_default_image
        prov.save()

    label = dict(AIProvider.PROVIDER_CHOICES).get(provider, provider)
    messages.success(request, f"{label} configurado com sucesso.")
    return redirect("core:ai_settings", project_id=project.id)


@login_required
@require_POST
def ai_provider_delete(request, project_id: int, provider_id: int):
    """Delete an AI provider."""
    from .models import AIProvider
    project = _get_user_project(request, project_id)
    prov = get_object_or_404(AIProvider, pk=provider_id, project=project)
    prov.delete()
    messages.success(request, "Provedor removido.")
    return redirect("core:ai_settings", project_id=project.id)


@login_required
@require_POST
def ai_provider_test(request, project_id: int):
    """Test an AI provider API key — AJAX. Receives provider + api_key in POST body."""
    from .ai_router import AIRouter
    _get_user_project(request, project_id)

    provider = request.POST.get("provider", "").strip()
    api_key = request.POST.get("api_key", "").strip()

    test_models = {
        "openai": "gpt-4.1-mini",
        "google": "gemini-2.5-flash",
        "anthropic": "claude-sonnet-4-20250514",
        "xai": "grok-3-mini",
    }
    model = test_models.get(provider, "")
    if not model or not api_key:
        return JsonResponse({"ok": False, "error": "Provedor ou API Key inválidos."})

    result = AIRouter.test_connection(provider, api_key, model)
    return JsonResponse(result)


# ══════════════════════════════════════════════════════════
# ── Admin Dashboard (admin-dev) ──────────────────────────
# ══════════════════════════════════════════════════════════

def _admin_required(view_fn):
    """Decorator: admin subdomain + login + superuser required."""
    from functools import wraps

    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        host = request.get_host().split(":")[0].lower()
        # Allow admin subdomain and localhost/127.0.0.1 for dev
        if not (host.startswith("admin.") or host in ("localhost", "127.0.0.1")):
            # Redirect to admin subdomain keeping the path
            from django.conf import settings as s
            admin_url = f"https://admin.{s.APP_DOMAIN}{request.get_full_path()}"
            return redirect(admin_url)
        if not request.user.is_authenticated:
            from django.conf import settings as s
            login_url = f"https://admin.{s.APP_DOMAIN}/login/?next={request.get_full_path()}"
            return redirect(login_url)
        if not request.user.is_superuser:
            return HttpResponseForbidden("Acesso restrito a administradores.")
        return view_fn(request, *args, **kwargs)
    return wrapper


def _admin_context(request, page: str) -> dict:
    """Base context for all admin-dev pages."""
    from .models import SystemErrorLog
    return {
        "admin_page": page,
        "unresolved_error_count": SystemErrorLog.objects.filter(resolved=False).count(),
        "admin_user_count": User.objects.count(),
    }


@_admin_required
def admin_overview(request):
    """Admin dashboard — system-wide stats and recent activity."""
    from .models import (
        AuditRecommendation, AuditReport, DataSnapshot, Project,
        ProjectScore, Site, SystemErrorLog,
    )
    from apps.channels.models import Channel

    now = timezone.now()
    last_30d = now - timedelta(days=30)
    last_24h = now - timedelta(hours=24)

    # User stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()

    # Project stats
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(is_active=True).count()

    # Audit stats
    total_audits = AuditReport.objects.count()
    audits_30d = AuditReport.objects.filter(created_at__gte=last_30d).count()
    scored_audits = AuditReport.objects.filter(overall_score__isnull=False, status="done")
    avg_score = scored_audits.aggregate(avg=Avg("overall_score"))["avg"]
    avg_score_int = int(avg_score) if avg_score else 0
    avg_score_dash = int(avg_score_int / 100 * 314) if avg_score_int else 0
    if avg_score_int >= 70:
        avg_score_color = "#22c55e"
    elif avg_score_int >= 40:
        avg_score_color = "#f59e0b"
    else:
        avg_score_color = "#ef4444"

    # Recommendation stats
    total_recs = AuditRecommendation.objects.count()
    applied_recs = AuditRecommendation.objects.filter(status="applied").count()
    pending_recs = AuditRecommendation.objects.filter(status="pending").count()
    dismissed_recs = AuditRecommendation.objects.filter(status="dismissed").count()
    recs_applied_pct = int(applied_recs / total_recs * 100) if total_recs > 0 else 0

    # Error stats
    unresolved_errors = SystemErrorLog.objects.filter(resolved=False).count()
    errors_24h = SystemErrorLog.objects.filter(timestamp__gte=last_24h).count()

    # Channel stats
    google_ads_channels = Channel.objects.filter(platform="google_ads", is_active=True).count()
    meta_ads_channels = Channel.objects.filter(platform="meta_ads", is_active=True).count()
    ga4_sites = Site.objects.filter(ga4_property_id__isnull=False).exclude(ga4_property_id="").count()

    # Recent items
    recent_audits = AuditReport.objects.select_related("project").prefetch_related("recommendations").order_by("-created_at")[:8]
    recent_errors = SystemErrorLog.objects.order_by("-timestamp")[:8]
    recent_users = User.objects.order_by("-date_joined")[:8]

    context = {
        **_admin_context(request, "overview"),
        "now": now,
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "total_projects": total_projects,
            "active_projects": active_projects,
            "total_audits": total_audits,
            "audits_30d": audits_30d,
            "unresolved_errors": unresolved_errors,
            "errors_24h": errors_24h,
            "avg_score": avg_score_int or None,
            "avg_score_dash": avg_score_dash,
            "avg_score_color": avg_score_color,
            "scored_audits": scored_audits.count(),
            "total_recs": total_recs,
            "applied_recs": applied_recs,
            "pending_recs": pending_recs,
            "dismissed_recs": dismissed_recs,
            "recs_applied_pct": recs_applied_pct,
            "google_ads_channels": google_ads_channels,
            "meta_ads_channels": meta_ads_channels,
            "ga4_sites": ga4_sites,
        },
        "recent_audits": recent_audits,
        "recent_errors": recent_errors,
        "recent_users": recent_users,
    }
    return render(request, "admin_dev/overview.html", context)


@_admin_required
def admin_users(request):
    """Admin — user management with search and filters."""
    from .models import Project

    q = request.GET.get("q", "").strip()
    f_role = request.GET.get("role", "")
    f_status = request.GET.get("status", "")

    qs = User.objects.all()
    if q:
        qs = qs.filter(
            Q(username__icontains=q) | Q(email__icontains=q)
        )
    if f_role == "superuser":
        qs = qs.filter(is_superuser=True)
    elif f_role == "staff":
        qs = qs.filter(is_staff=True, is_superuser=False)
    elif f_role == "user":
        qs = qs.filter(is_staff=False, is_superuser=False)
    if f_status == "active":
        qs = qs.filter(is_active=True)
    elif f_status == "inactive":
        qs = qs.filter(is_active=False)

    qs = qs.order_by("-date_joined")

    # Annotate project count
    from django.db.models import Count
    qs = qs.annotate(project_count=Count("projects"))

    # Stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    staff_users = User.objects.filter(is_staff=True).count()
    super_users = User.objects.filter(is_superuser=True).count()

    # Pagination
    page = int(request.GET.get("page", 1))
    per_page = 25
    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    users = qs[(page - 1) * per_page : page * per_page]

    context = {
        **_admin_context(request, "users"),
        "users": users,
        "total_users": total_users,
        "active_users": active_users,
        "staff_users": staff_users,
        "super_users": super_users,
        "q": q,
        "f_role": f_role,
        "f_status": f_status,
        "page": page,
        "total_pages": total_pages,
        "page_range": range(max(1, page - 3), min(total_pages + 1, page + 4)),
    }
    return render(request, "admin_dev/users.html", context)


@_admin_required
@require_POST
def admin_user_toggle(request, user_id: int):
    """Toggle a user's is_active status."""
    target = get_object_or_404(User, pk=user_id)
    if target.is_superuser:
        return JsonResponse({"error": "Não pode desativar superuser"}, status=403)
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    messages.success(request, f"Usuário {target.username} {'ativado' if target.is_active else 'desativado'}.")
    return redirect("core:admin_users")


@_admin_required
@require_POST
def admin_user_staff_toggle(request, user_id: int):
    """Toggle a user's is_staff status."""
    target = get_object_or_404(User, pk=user_id)
    if target.is_superuser:
        return JsonResponse({"error": "Não pode alterar superuser"}, status=403)
    target.is_staff = not target.is_staff
    target.save(update_fields=["is_staff"])
    messages.success(request, f"Usuário {target.username}: staff={'sim' if target.is_staff else 'não'}.")
    return redirect("core:admin_users")


@_admin_required
def admin_projects(request):
    """Admin — all projects with stats."""
    from .models import AuditReport, Project, ProjectScore
    from apps.channels.models import Channel

    q = request.GET.get("q", "").strip()
    f_status = request.GET.get("status", "")

    qs = Project.objects.select_related("owner").all()
    if q:
        qs = qs.filter(name__icontains=q)
    if f_status == "active":
        qs = qs.filter(is_active=True)
    elif f_status == "inactive":
        qs = qs.filter(is_active=False)

    qs = qs.order_by("-created_at")

    projects = []
    for p in qs:
        p.site_count = p.sites.count()
        p.channel_count = Channel.objects.filter(
            project=p, is_active=True
        ).count()
        p.audit_count = AuditReport.objects.filter(project=p).count()
        p.score = ProjectScore.objects.filter(project=p).first()
        p.latest_audit = AuditReport.objects.filter(
            project=p, status="done"
        ).order_by("-created_at").first()
        p.has_google_ads = Channel.objects.filter(
            project=p, platform="google_ads", is_active=True
        ).exists()
        p.has_meta_ads = Channel.objects.filter(
            project=p, platform="meta_ads", is_active=True
        ).exists()
        p.has_ga4 = p.sites.filter(ga4_property_id__isnull=False).exclude(ga4_property_id="").exists()
        projects.append(p)

    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(is_active=True).count()
    total_sites = Site.objects.count()
    total_channels = Channel.objects.filter(is_active=True).count()

    context = {
        **_admin_context(request, "projects"),
        "projects": projects,
        "total_projects": total_projects,
        "active_projects": active_projects,
        "total_sites": total_sites,
        "total_channels": total_channels,
        "q": q,
        "f_status": f_status,
    }
    return render(request, "admin_dev/projects.html", context)


@_admin_required
def admin_audits(request):
    """Admin — all audits across all projects."""
    from .models import AuditRecommendation, AuditReport, Project

    f_project = request.GET.get("project", "")
    f_status = request.GET.get("status", "")
    f_date_from = request.GET.get("date_from", "")

    qs = AuditReport.objects.select_related("project", "project__owner").order_by("-created_at")
    if f_project:
        qs = qs.filter(project_id=f_project)
    if f_status:
        qs = qs.filter(status=f_status)
    if f_date_from:
        try:
            qs = qs.filter(created_at__date__gte=f_date_from)
        except (ValueError, TypeError):
            pass

    # Stats
    all_audits = AuditReport.objects.all()
    total_audits = all_audits.count()
    done_audits = all_audits.filter(status="done").count()
    running_audits = all_audits.filter(status="running").count()
    error_audits = all_audits.filter(status="error").count()
    avg_score_raw = all_audits.filter(
        overall_score__isnull=False, status="done"
    ).aggregate(avg=Avg("overall_score"))["avg"]
    avg_score = int(avg_score_raw) if avg_score_raw else None

    # Pagination
    page = int(request.GET.get("page", 1))
    per_page = 20
    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    audits = list(qs[(page - 1) * per_page : page * per_page])

    # Annotate rec counts
    for a in audits:
        a.rec_count = a.recommendations.count()
        a.applied_count = a.recommendations.filter(status="applied").count()

    all_projects = Project.objects.filter(is_active=True).order_by("name")

    context = {
        **_admin_context(request, "audits"),
        "audits": audits,
        "total_audits": total_audits,
        "done_audits": done_audits,
        "running_audits": running_audits,
        "error_audits": error_audits,
        "avg_score": avg_score,
        "all_projects": all_projects,
        "f_project": f_project,
        "f_status": f_status,
        "f_date_from": f_date_from,
        "page": page,
        "total_pages": total_pages,
        "page_range": range(max(1, page - 3), min(total_pages + 1, page + 4)),
    }
    return render(request, "admin_dev/audits.html", context)


@_admin_required
def admin_errors(request):
    """Admin — error logs (replaces old error_dashboard)."""
    from .models import SystemErrorLog

    error_type = request.GET.get("error_type", "")
    severity = request.GET.get("severity", "")
    resolved = request.GET.get("resolved", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    qs = SystemErrorLog.objects.all()
    if error_type:
        qs = qs.filter(error_type=error_type)
    if severity:
        qs = qs.filter(severity=severity)
    if resolved == "yes":
        qs = qs.filter(resolved=True)
    elif resolved == "no":
        qs = qs.filter(resolved=False)
    if date_from:
        try:
            qs = qs.filter(timestamp__date__gte=date_from)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            qs = qs.filter(timestamp__date__lte=date_to)
        except (ValueError, TypeError):
            pass

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    total_24h = SystemErrorLog.objects.filter(timestamp__gte=last_24h).count()
    unresolved = SystemErrorLog.objects.filter(resolved=False).count()
    most_common = ""
    common_qs = SystemErrorLog.objects.filter(
        timestamp__gte=last_24h,
    ).values("error_type").annotate(count=Sum("id")).order_by("-count").first()
    if common_qs:
        for choice in SystemErrorLog.ERROR_TYPE_CHOICES:
            if choice[0] == common_qs["error_type"]:
                most_common = choice[1]
                break

    page = int(request.GET.get("page", 1))
    per_page = 30
    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    errors = qs[(page - 1) * per_page : page * per_page]

    context = {
        **_admin_context(request, "errors"),
        "errors": errors,
        "total": total,
        "total_24h": total_24h,
        "unresolved": unresolved,
        "most_common": most_common,
        "error_type_choices": SystemErrorLog.ERROR_TYPE_CHOICES,
        "severity_choices": SystemErrorLog.SEVERITY_CHOICES,
        "f_error_type": error_type,
        "f_severity": severity,
        "f_resolved": resolved,
        "f_date_from": date_from,
        "f_date_to": date_to,
        "page": page,
        "total_pages": total_pages,
        "page_range": range(max(1, page - 3), min(total_pages + 1, page + 4)),
    }
    return render(request, "admin_dev/errors.html", context)


@_admin_required
@require_POST
def admin_error_resolve(request, error_id: int):
    """Toggle resolved status of an error."""
    from .models import SystemErrorLog
    err = get_object_or_404(SystemErrorLog, pk=error_id)
    err.resolved = not err.resolved
    err.save(update_fields=["resolved"])
    return JsonResponse({"success": True, "resolved": err.resolved})


@_admin_required
@require_POST
def admin_error_notes(request, error_id: int):
    """Update developer notes on an error."""
    from .models import SystemErrorLog
    err = get_object_or_404(SystemErrorLog, pk=error_id)
    data = json.loads(request.body) if request.content_type == "application/json" else request.POST
    err.developer_notes = data.get("developer_notes", "")
    err.save(update_fields=["developer_notes"])
    return JsonResponse({"success": True})


@_admin_required
def admin_system(request):
    """Admin — system info, environment, API keys, cache."""
    import django
    import platform
    import sys

    from .models import DataSnapshot

    # Environment
    env_info = {
        "Python": sys.version.split()[0],
        "Django": django.get_version(),
        "OS": platform.platform(),
        "Timezone": str(timezone.get_current_timezone()),
        "Language": getattr(settings, "LANGUAGE_CODE", "?"),
        "DEBUG": str(getattr(settings, "DEBUG", False)),
    }

    # API Keys
    api_keys = {
        "OPENAI_API_KEY": bool(getattr(settings, "OPENAI_API_KEY", "")),
        "GEMINI_API_KEY": bool(getattr(settings, "GEMINI_API_KEY", "")),
        "GOOGLE_ADS_DEVELOPER_TOKEN": bool(getattr(settings, "GOOGLE_ADS_DEVELOPER_TOKEN", "")),
        "GOOGLE_ADS_CLIENT_ID": bool(getattr(settings, "GOOGLE_ADS_CLIENT_ID", "")),
        "META_APP_ID": bool(getattr(settings, "META_APP_ID", "")),
    }

    # Database info
    db_conf = settings.DATABASES.get("default", {})
    db_name = str(db_conf.get("NAME", "?"))
    db_info = {
        "Engine": str(db_conf.get("ENGINE", "?")).split(".")[-1],
        "Name": db_name.split("/")[-1] if db_name else "?",
    }

    # Cache stats
    now = timezone.now()
    total_snapshots = DataSnapshot.objects.count()
    valid_snapshots = DataSnapshot.objects.filter(expires_at__gt=now).count()
    expired_snapshots = total_snapshots - valid_snapshots
    distinct_types = DataSnapshot.objects.values("data_type").distinct().count()

    cache_stats = {
        "total": total_snapshots,
        "valid": valid_snapshots,
        "expired": expired_snapshots,
        "types": distinct_types,
    }

    context = {
        **_admin_context(request, "system"),
        "env_info": env_info,
        "api_keys": api_keys,
        "db_info": db_info,
        "cache_stats": cache_stats,
        "installed_apps": settings.INSTALLED_APPS,
        "middleware": settings.MIDDLEWARE,
    }
    return render(request, "admin_dev/system.html", context)