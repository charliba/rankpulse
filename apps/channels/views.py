"""Channel views — CRUD for channels, credentials, ads API proxy, and OAuth flows."""
from __future__ import annotations

import json
import logging
import urllib.parse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import Project

from .forms import ChannelCredentialForm, ChannelForm
from .models import Channel, ChannelCredential

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────

def _get_user_project(request, project_id: int) -> Project:
    """Return a project that belongs to the current user."""
    return get_object_or_404(Project, pk=project_id, owner=request.user)


def _get_user_channel(request, channel_id: int) -> Channel:
    """Return a channel whose project belongs to the current user."""
    return get_object_or_404(
        Channel.objects.select_related("project"),
        pk=channel_id,
        project__owner=request.user,
    )


def _get_ads_manager(channel: Channel):
    """Build a GoogleAdsManager from channel credentials."""
    from apps.analytics.ads_client import GoogleAdsManager

    try:
        cred = channel.credentials
    except ChannelCredential.DoesNotExist:
        raise ValueError("Canal sem credenciais configuradas.")

    return GoogleAdsManager(
        customer_id=cred.customer_id,
        developer_token=cred.developer_token,
        client_id=cred.client_id,
        client_secret=cred.client_secret,
        refresh_token=cred.refresh_token,
        login_customer_id=cred.login_customer_id,
    )


# ── Channel CRUD ───────────────────────────────────────────────

@login_required
def channel_add(request, project_id: int):
    """Create a new channel inside a project."""
    project = _get_user_project(request, project_id)

    if request.method == "POST":
        form = ChannelForm(request.POST)
        if form.is_valid():
            channel = form.save(commit=False)
            channel.project = project
            channel.save()
            # Auto-create empty credential record
            ChannelCredential.objects.create(channel=channel)
            messages.success(request, f"Canal '{channel.name}' criado!")
            return redirect("channels:channel_credentials", channel_id=channel.pk)
    else:
        form = ChannelForm()

    return render(request, "channels/channel_form.html", {
        "page_title": "Adicionar Canal",
        "project": project,
        "form": form,
    })


@login_required
def channel_credentials(request, channel_id: int):
    """Edit channel credentials."""
    channel = _get_user_channel(request, channel_id)
    cred, _ = ChannelCredential.objects.get_or_create(channel=channel)

    if request.method == "POST":
        form = ChannelCredentialForm(request.POST, instance=cred)
        if form.is_valid():
            form.save()
            messages.success(request, "Credenciais salvas!")
            return redirect("channels:channel_credentials", channel_id=channel.pk)
    else:
        form = ChannelCredentialForm(instance=cred)

    return render(request, "channels/channel_credentials.html", {
        "page_title": f"Credenciais — {channel.name}",
        "channel": channel,
        "project": channel.project,
        "form": form,
        "is_configured": channel.is_configured,
    })


@login_required
def channel_delete(request, channel_id: int):
    """Delete a channel (POST only)."""
    channel = _get_user_channel(request, channel_id)
    project = channel.project
    if request.method == "POST":
        name = channel.name
        channel.delete()
        messages.success(request, f"Canal '{name}' removido.")
    return redirect("core:project_detail", project_id=project.pk)


# ── Google Ads OAuth Flow (channel-scoped) ─────────────────────

GOOGLE_ADS_SCOPES = ["https://www.googleapis.com/auth/adwords"]
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


@login_required
def google_ads_oauth_start(request, channel_id: int):
    """Generate the Google OAuth2 authorization URL for a channel."""
    channel = _get_user_channel(request, channel_id)
    cred = getattr(channel, "credentials", None)

    client_id = cred.client_id if cred else ""
    if not client_id:
        return JsonResponse(
            {"error": "Preencha o OAuth Client ID antes de gerar o token."},
            status=400,
        )

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
def google_ads_oauth_exchange(request, channel_id: int):
    """Exchange an authorization code for refresh + access tokens (channel-scoped)."""
    channel = _get_user_channel(request, channel_id)
    cred = getattr(channel, "credentials", None)

    auth_code = request.POST.get("auth_code", "").strip()
    if not auth_code:
        return JsonResponse({"error": "Informe o código de autorização."}, status=400)

    if not cred or not cred.client_id or not cred.client_secret:
        return JsonResponse(
            {"error": "Preencha Client ID e Client Secret antes."},
            status=400,
        )

    import requests as http_requests

    try:
        resp = http_requests.post(
            GOOGLE_TOKEN_URI,
            data={
                "code": auth_code,
                "client_id": cred.client_id,
                "client_secret": cred.client_secret,
                "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                "grant_type": "authorization_code",
            },
            timeout=30,
        )
        token_data = resp.json()
    except Exception as exc:
        logger.exception("OAuth token exchange failed")
        return JsonResponse({"error": f"Erro ao contatar o Google: {exc}"}, status=502)

    if "error" in token_data:
        error_desc = token_data.get("error_description", token_data["error"])
        return JsonResponse({"error": f"Google retornou erro: {error_desc}"}, status=400)

    refresh_token = token_data.get("refresh_token", "")
    if not refresh_token:
        return JsonResponse(
            {"error": "Google não retornou refresh_token. Tente novamente com prompt=consent."},
            status=400,
        )

    cred.refresh_token = refresh_token
    cred.save(update_fields=["refresh_token"])

    logger.info("Google Ads refresh token saved for channel %s (pk=%d)", channel.name, channel.pk)

    return JsonResponse({
        "success": True,
        "message": f"Refresh Token salvo com sucesso! ({len(refresh_token)} caracteres)",
        "token_preview": f"{refresh_token[:15]}...{refresh_token[-8:]}",
    })


@login_required
@require_POST
def google_ads_test_connection(request, channel_id: int):
    """Test the Google Ads API connection with current channel credentials."""
    channel = _get_user_channel(request, channel_id)

    if not channel.is_configured:
        return JsonResponse(
            {"error": "Preencha todas as credenciais do Google Ads primeiro."},
            status=400,
        )

    cred = channel.credentials
    import requests as http_requests

    try:
        resp = http_requests.post(
            GOOGLE_TOKEN_URI,
            data={
                "client_id": cred.client_id,
                "client_secret": cred.client_secret,
                "refresh_token": cred.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        data = resp.json()
    except Exception as exc:
        return JsonResponse({"error": f"Erro de conexão: {exc}"}, status=502)

    if "error" in data:
        error_map = {
            "invalid_grant": "Token inválido ou expirado. Gere um novo Refresh Token.",
            "invalid_client": "Client ID ou Client Secret incorretos.",
            "unauthorized_client": "Este cliente OAuth não está autorizado.",
        }
        error_code = data.get("error", "")
        friendly_msg = error_map.get(error_code, data.get("error_description", error_code))
        return JsonResponse({"error": friendly_msg, "error_code": error_code}, status=400)

    return JsonResponse({
        "success": True,
        "message": "Conexão com Google Ads API OK! Access token obtido com sucesso.",
    })


# ── Google Ads API Proxy (channel-scoped) ──────────────────────

@login_required
@require_GET
def ads_account_info(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/ads/account/"""
    channel = _get_user_channel(request, channel_id)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.get_account_info())


@login_required
@require_GET
def ads_campaigns(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/ads/campaigns/"""
    channel = _get_user_channel(request, channel_id)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.list_campaigns())


@login_required
@require_POST
def ads_create_campaign(request, channel_id: int) -> JsonResponse:
    """POST /api/channels/<channel_id>/ads/campaigns/create/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.create_campaign(
        name=body.get("name", ""),
        daily_budget_brl=float(body.get("daily_budget_brl", 50.0)),
        bidding_strategy=body.get("bidding_strategy", "MAXIMIZE_CONVERSIONS"),
    ))


@login_required
@require_POST
def ads_update_campaign_status(request, channel_id: int) -> JsonResponse:
    """POST /api/channels/<channel_id>/ads/campaigns/status/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.update_campaign_status(
        campaign_id=body.get("campaign_id", ""),
        status=body.get("status", "ENABLED"),
    ))


@login_required
@require_POST
def ads_update_budget(request, channel_id: int) -> JsonResponse:
    """POST /api/channels/<channel_id>/ads/campaigns/budget/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.update_campaign_budget_amount(
        campaign_id=body.get("campaign_id", ""),
        new_daily_budget_brl=float(body.get("daily_budget_brl", 50.0)),
    ))


@login_required
@require_GET
def ads_ad_groups(request, channel_id: int, campaign_id: str) -> JsonResponse:
    """GET /api/channels/<channel_id>/ads/campaigns/<campaign_id>/ad-groups/"""
    channel = _get_user_channel(request, channel_id)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.list_ad_groups(campaign_id))


@login_required
@require_POST
def ads_create_ad_group(request, channel_id: int, campaign_id: str) -> JsonResponse:
    """POST /api/channels/<channel_id>/ads/campaigns/<campaign_id>/ad-groups/create/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.create_ad_group(
        campaign_id=campaign_id,
        name=body.get("name", ""),
        cpc_bid_brl=float(body.get("cpc_bid_brl", 2.0)),
    ))


@login_required
@require_POST
def ads_add_keywords(request, channel_id: int, ad_group_id: str) -> JsonResponse:
    """POST /api/channels/<channel_id>/ads/ad-groups/<ad_group_id>/keywords/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.add_keywords(
        ad_group_id=ad_group_id,
        keywords=body.get("keywords", []),
    ))


@login_required
@require_POST
def ads_create_rsa(request, channel_id: int, ad_group_id: str) -> JsonResponse:
    """POST /api/channels/<channel_id>/ads/ad-groups/<ad_group_id>/rsa/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.create_responsive_search_ad(
        ad_group_id=ad_group_id,
        headlines=body.get("headlines", []),
        descriptions=body.get("descriptions", []),
        final_url=body.get("final_url", ""),
        path1=body.get("path1", ""),
        path2=body.get("path2", ""),
    ))


@login_required
@require_GET
def ads_conversions(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/ads/conversions/"""
    channel = _get_user_channel(request, channel_id)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.list_conversion_actions())


@login_required
@require_POST
def ads_create_conversion(request, channel_id: int) -> JsonResponse:
    """POST /api/channels/<channel_id>/ads/conversions/create/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.create_conversion_action(
        name=body.get("name", ""),
        category=body.get("category", "PURCHASE"),
        value_settings=body.get("value_settings"),
    ))


@login_required
@require_GET
def ads_campaign_performance(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/ads/performance/?campaign_id=X&days=30"""
    channel = _get_user_channel(request, channel_id)
    campaign_id = request.GET.get("campaign_id")
    days = int(request.GET.get("days", 30))
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.get_campaign_performance(campaign_id=campaign_id, days=days))


@login_required
@require_GET
def ads_keyword_performance(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/ads/keyword-performance/?campaign_id=X&days=30"""
    channel = _get_user_channel(request, channel_id)
    campaign_id = request.GET.get("campaign_id")
    days = int(request.GET.get("days", 30))
    mgr = _get_ads_manager(channel)
    return JsonResponse(mgr.get_keyword_performance(campaign_id=campaign_id, days=days))
