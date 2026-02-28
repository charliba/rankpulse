"""Core views — Dashboard, Site CRUD, reports, and OAuth flows."""
from __future__ import annotations

import json
import logging
import urllib.parse

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Sum
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import GA4EventForm, IntegrationsForm, KPIGoalForm, SiteForm
from .models import GA4EventDefinition, KPIGoal, Site, WeeklySnapshot

logger = logging.getLogger(__name__)


def _base_context(request) -> dict:
    """Common context for all views — user's sites list for sidebar."""
    return {"sites": Site.objects.filter(owner=request.user, is_active=True)}


def _get_user_site(request, site_id: int) -> Site:
    """Get a site that belongs to the current user."""
    return get_object_or_404(Site, pk=site_id, owner=request.user)


# ── Dashboard ──────────────────────────────────────────

@login_required
def dashboard(request):
    """Main dashboard showing user's sites overview."""
    sites = Site.objects.filter(owner=request.user, is_active=True)
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
        "page_title": "Dashboard",
        "site_data": site_data,
        "total_sites": sites.count(),
    }
    return render(request, "core/dashboard.html", context)


# ── Site CRUD ──────────────────────────────────────────

@login_required
def site_add(request):
    """Create a new site."""
    if request.method == "POST":
        form = SiteForm(request.POST)
        if form.is_valid():
            site = form.save(commit=False)
            site.owner = request.user
            site.save()
            messages.success(request, f"Site '{site.name}' criado com sucesso!")
            return redirect("core:site_detail", site_id=site.pk)
    else:
        form = SiteForm()

    context = {
        **_base_context(request),
        "page_title": "Adicionar Site",
        "form": form,
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
        "editing": True,
    }
    return render(request, "core/site_form.html", context)


@login_required
def site_delete(request, site_id: int):
    """Delete a site (POST only)."""
    site = _get_user_site(request, site_id)
    if request.method == "POST":
        name = site.name
        site.delete()
        messages.success(request, f"Site '{name}' removido.")
        return redirect("core:dashboard")
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
    """Integrations settings page — Google Ads, GA4, GSC credentials."""
    site = _get_user_site(request, site_id)

    if request.method == "POST":
        form = IntegrationsForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, "Integrações salvas com sucesso!")
            return redirect("core:site_integrations", site_id=site.pk)
    else:
        form = IntegrationsForm(instance=site)

    # Status checks
    integrations_status = {
        "ga4": bool(site.ga4_measurement_id),
        "ga4_api": bool(site.ga4_api_secret),
        "ga4_property": bool(site.ga4_property_id),
        "ga4_service_account": bool(site.ga4_service_account_key),
        "gsc": site.gsc_verified,
        "gsc_service_account": bool(site.gsc_service_account_key),
        "google_ads": site.google_ads_configured,
    }

    context = {
        **_base_context(request),
        "page_title": "Integrações",
        "site": site,
        "form": form,
        "status": integrations_status,
    }
    return render(request, "core/site_integrations.html", context)


# ── Google Ads OAuth Flow ─────────────────────────────

GOOGLE_ADS_SCOPES = ["https://www.googleapis.com/auth/adwords"]
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


@login_required
def google_ads_oauth_start(request, site_id: int):
    """Generate the Google OAuth2 authorization URL.

    Returns JSON with the auth URL. The user opens this in a new tab,
    authorizes, and Google shows an authorization code to copy back.
    """
    site = _get_user_site(request, site_id)

    client_id = site.google_ads_client_id
    if not client_id:
        return JsonResponse(
            {"error": "Preencha o OAuth Client ID antes de gerar o token."},
            status=400,
        )

    # Use OOB redirect for Desktop app OAuth clients
    redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(GOOGLE_ADS_SCOPES),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
    }

    auth_url = f"{GOOGLE_AUTH_URI}?{urllib.parse.urlencode(params)}"
    return JsonResponse({"auth_url": auth_url})


@login_required
@require_POST
def google_ads_oauth_exchange(request, site_id: int):
    """Exchange an authorization code for refresh + access tokens.

    Saves the refresh token directly to the Site model.
    """
    site = _get_user_site(request, site_id)

    auth_code = request.POST.get("auth_code", "").strip()
    if not auth_code:
        return JsonResponse(
            {"error": "Informe o codigo de autorizacao."},
            status=400,
        )

    client_id = site.google_ads_client_id
    client_secret = site.google_ads_client_secret
    if not client_id or not client_secret:
        return JsonResponse(
            {"error": "Preencha Client ID e Client Secret antes."},
            status=400,
        )

    # Exchange authorization code for tokens
    import requests as http_requests

    try:
        resp = http_requests.post(
            GOOGLE_TOKEN_URI,
            data={
                "code": auth_code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                "grant_type": "authorization_code",
            },
            timeout=30,
        )
        token_data = resp.json()
    except Exception as exc:
        logger.exception("OAuth token exchange failed")
        return JsonResponse(
            {"error": f"Erro ao contatar o Google: {exc}"},
            status=502,
        )

    if "error" in token_data:
        error_desc = token_data.get("error_description", token_data["error"])
        return JsonResponse({"error": f"Google retornou erro: {error_desc}"}, status=400)

    refresh_token = token_data.get("refresh_token", "")
    if not refresh_token:
        return JsonResponse(
            {"error": "Google nao retornou refresh_token. Tente novamente com prompt=consent."},
            status=400,
        )

    # Save to database
    site.google_ads_refresh_token = refresh_token
    site.save(update_fields=["google_ads_refresh_token"])

    logger.info("Google Ads refresh token saved for site %s (pk=%d)", site.name, site.pk)

    return JsonResponse({
        "success": True,
        "message": f"Refresh Token salvo com sucesso! ({len(refresh_token)} caracteres)",
        "token_preview": f"{refresh_token[:15]}...{refresh_token[-8:]}",
    })


@login_required
@require_POST
def google_ads_test_connection(request, site_id: int):
    """Test the Google Ads API connection with current credentials.

    Returns JSON indicating success or a detailed error message.
    """
    site = _get_user_site(request, site_id)

    if not site.google_ads_configured:
        return JsonResponse(
            {"error": "Preencha todas as credenciais do Google Ads primeiro."},
            status=400,
        )

    # Test the refresh token by exchanging it for an access token
    import requests as http_requests

    try:
        resp = http_requests.post(
            GOOGLE_TOKEN_URI,
            data={
                "client_id": site.google_ads_client_id,
                "client_secret": site.google_ads_client_secret,
                "refresh_token": site.google_ads_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        data = resp.json()
    except Exception as exc:
        return JsonResponse({"error": f"Erro de conexao: {exc}"}, status=502)

    if "error" in data:
        error_map = {
            "invalid_grant": (
                "Token invalido ou expirado. Gere um novo Refresh Token "
                "usando o botao 'Gerar Refresh Token' acima."
            ),
            "invalid_client": (
                "Client ID ou Client Secret incorretos. Verifique as "
                "credenciais no Google Cloud Console."
            ),
            "unauthorized_client": (
                "Este cliente OAuth nao esta autorizado. Verifique se a "
                "Google Ads API esta ativada no projeto Google Cloud."
            ),
        }
        error_code = data.get("error", "")
        friendly_msg = error_map.get(error_code, data.get("error_description", error_code))
        return JsonResponse({"error": friendly_msg, "error_code": error_code}, status=400)

    return JsonResponse({
        "success": True,
        "message": "Conexao com Google Ads API OK! Access token obtido com sucesso.",
    })
