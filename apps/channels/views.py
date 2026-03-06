"""Channel views — CRUD for channels, credentials, ads API proxy, and OAuth flows."""
from __future__ import annotations

import json
import logging
import os
import urllib.parse

from django.conf import settings
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


# ── Meta Ads Helpers ───────────────────────────────────────────

META_APP_ID = os.environ.get("META_APP_ID", "")
META_APP_SECRET = os.environ.get("META_APP_SECRET", "")
META_GRAPH_VERSION = "v21.0"
META_OAUTH_SCOPES = "ads_management,ads_read,business_management"


def _get_meta_manager(channel: Channel):
    """Build a MetaAdsManager from channel credentials."""
    from apps.analytics.meta_ads_client import MetaAdsManager

    try:
        cred = channel.credentials
    except ChannelCredential.DoesNotExist:
        raise ValueError("Canal sem credenciais configuradas.")

    if not cred.access_token or not cred.account_id:
        raise ValueError("Access Token e Account ID são obrigatórios para Meta Ads.")

    return MetaAdsManager(
        access_token=cred.access_token,
        account_id=cred.account_id,
        app_id=META_APP_ID,
        app_secret=META_APP_SECRET,
    )


# ── Meta Ads OAuth Flow ───────────────────────────────────────

@login_required
def meta_oauth_start(request, channel_id: int):
    """Redirect user to Facebook OAuth dialog to authorize Meta Ads access."""
    channel = _get_user_channel(request, channel_id)

    if not META_APP_ID:
        return JsonResponse(
            {"error": "META_APP_ID não configurado no servidor."},
            status=400,
        )

    app_domain = os.environ.get("APP_DOMAIN", "rankpulse.cloud")
    redirect_uri = f"https://app.{app_domain}/channels/oauth/meta/callback/"

    params = {
        "client_id": META_APP_ID,
        "redirect_uri": redirect_uri,
        "scope": META_OAUTH_SCOPES,
        "response_type": "code",
        "state": str(channel.pk),
    }

    auth_url = f"https://www.facebook.com/{META_GRAPH_VERSION}/dialog/oauth?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


@login_required
def meta_oauth_callback(request):
    """Handle Facebook OAuth callback — exchange code for long-lived token."""
    code = request.GET.get("code", "")
    error = request.GET.get("error", "")
    state = request.GET.get("state", "")

    if not state:
        messages.error(request, "Parâmetro state ausente no callback.")
        return redirect("core:dashboard")

    channel_id = int(state)
    channel = _get_user_channel(request, channel_id)

    if error:
        error_reason = request.GET.get("error_reason", "")
        messages.error(request, f"Meta OAuth negado: {error_reason or error}")
        return redirect("channels:channel_credentials", channel_id=channel.pk)

    if not code:
        messages.error(request, "Código de autorização não recebido do Facebook.")
        return redirect("channels:channel_credentials", channel_id=channel.pk)

    import requests as http_requests

    app_domain = os.environ.get("APP_DOMAIN", "rankpulse.cloud")
    redirect_uri = f"https://app.{app_domain}/channels/oauth/meta/callback/"

    # Exchange code for short-lived token
    try:
        resp = http_requests.get(
            f"https://graph.facebook.com/{META_GRAPH_VERSION}/oauth/access_token",
            params={
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=30,
        )
        data = resp.json()
    except Exception as exc:
        logger.exception("Meta OAuth token exchange failed")
        messages.error(request, f"Erro ao contatar o Facebook: {exc}")
        return redirect("channels:channel_credentials", channel_id=channel.pk)

    if "error" in data:
        error_msg = data["error"].get("message", str(data["error"]))
        messages.error(request, f"Facebook retornou erro: {error_msg}")
        return redirect("channels:channel_credentials", channel_id=channel.pk)

    short_token = data.get("access_token", "")

    # Exchange for long-lived token (60 days)
    from apps.analytics.meta_ads_client import MetaAdsManager
    long_result = MetaAdsManager.exchange_short_lived_token(
        app_id=META_APP_ID,
        app_secret=META_APP_SECRET,
        short_lived_token=short_token,
    )

    if not long_result["success"]:
        # Fall back to short-lived token
        logger.warning("Failed to get long-lived token, using short-lived: %s", long_result["error"])
        final_token = short_token
    else:
        final_token = long_result["access_token"]

    # Save token to credentials
    cred, _ = ChannelCredential.objects.get_or_create(channel=channel)
    cred.access_token = final_token

    # Auto-fetch ad account ID
    try:
        acct_resp = http_requests.get(
            f"https://graph.facebook.com/{META_GRAPH_VERSION}/me/adaccounts",
            params={"access_token": final_token, "fields": "id,name", "limit": 1},
            timeout=15,
        )
        acct_data = acct_resp.json()
        accounts = acct_data.get("data", [])
        if accounts:
            cred.account_id = accounts[0]["id"]
            logger.info("Auto-detected ad account: %s (%s)", accounts[0]["id"], accounts[0].get("name", ""))
    except Exception:
        logger.warning("Could not auto-detect ad account ID", exc_info=True)

    cred.save(update_fields=["access_token", "account_id"])

    logger.info("Meta access token saved for channel %s (pk=%d)", channel.name, channel.pk)
    messages.success(request, "Meta Ads conectado com sucesso! Access Token salvo.")
    return redirect("channels:channel_credentials", channel_id=channel.pk)


@login_required
@require_POST
def meta_test_connection(request, channel_id: int) -> JsonResponse:
    """Test the Meta Ads API connection with current credentials."""
    channel = _get_user_channel(request, channel_id)

    if channel.platform != "meta_ads":
        return JsonResponse({"error": "Canal não é Meta Ads."}, status=400)

    try:
        mgr = _get_meta_manager(channel)
        result = mgr.get_account_info()
        if result["success"]:
            return JsonResponse({
                "success": True,
                "message": f"Conexão OK! Conta: {result['name']} ({result['id']}) — {result['status']}",
            })
        return JsonResponse({"error": result["error"]}, status=400)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"error": f"Erro: {exc}"}, status=502)


# ── Meta Ads API Proxy ─────────────────────────────────────────

@login_required
@require_GET
def meta_account_info(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/meta/account/"""
    channel = _get_user_channel(request, channel_id)
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.get_account_info())


@login_required
@require_GET
def meta_campaigns(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/meta/campaigns/"""
    channel = _get_user_channel(request, channel_id)
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.list_campaigns())


@login_required
@require_POST
def meta_create_campaign(request, channel_id: int) -> JsonResponse:
    """POST /api/channels/<channel_id>/meta/campaigns/create/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.create_campaign(
        name=body.get("name", ""),
        objective=body.get("objective", "OUTCOME_TRAFFIC"),
        daily_budget_brl=body.get("daily_budget_brl"),
        lifetime_budget_brl=body.get("lifetime_budget_brl"),
        status=body.get("status", "PAUSED"),
        special_ad_categories=body.get("special_ad_categories"),
    ))


@login_required
@require_POST
def meta_update_campaign_status(request, channel_id: int) -> JsonResponse:
    """POST /api/channels/<channel_id>/meta/campaigns/status/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.update_campaign_status(
        campaign_id=body.get("campaign_id", ""),
        status=body.get("status", "PAUSED"),
    ))


@login_required
@require_GET
def meta_ad_sets(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/meta/ad-sets/?campaign_id=X"""
    channel = _get_user_channel(request, channel_id)
    campaign_id = request.GET.get("campaign_id")
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.list_ad_sets(campaign_id=campaign_id))


@login_required
@require_POST
def meta_create_ad_set(request, channel_id: int) -> JsonResponse:
    """POST /api/channels/<channel_id>/meta/ad-sets/create/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.create_ad_set(
        campaign_id=body.get("campaign_id", ""),
        name=body.get("name", ""),
        daily_budget_brl=float(body.get("daily_budget_brl", 20.0)),
        billing_event=body.get("billing_event", "IMPRESSIONS"),
        optimization_goal=body.get("optimization_goal", "LINK_CLICKS"),
        targeting=body.get("targeting"),
        status=body.get("status", "PAUSED"),
        start_time=body.get("start_time"),
    ))


@login_required
@require_POST
def meta_update_ad_set_status(request, channel_id: int) -> JsonResponse:
    """POST /api/channels/<channel_id>/meta/ad-sets/status/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.update_ad_set_status(
        ad_set_id=body.get("ad_set_id", ""),
        status=body.get("status", "PAUSED"),
    ))


@login_required
@require_GET
def meta_ads_list(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/meta/ads/?ad_set_id=X"""
    channel = _get_user_channel(request, channel_id)
    ad_set_id = request.GET.get("ad_set_id")
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.list_ads(ad_set_id=ad_set_id))


@login_required
@require_POST
def meta_create_ad(request, channel_id: int) -> JsonResponse:
    """POST /api/channels/<channel_id>/meta/ads/create/"""
    channel = _get_user_channel(request, channel_id)
    body = json.loads(request.body)
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.create_ad(
        ad_set_id=body.get("ad_set_id", ""),
        name=body.get("name", ""),
        creative_id=body.get("creative_id"),
        page_id=body.get("page_id"),
        link_url=body.get("link_url"),
        message=body.get("message"),
        image_hash=body.get("image_hash"),
        status=body.get("status", "PAUSED"),
    ))


@login_required
@require_GET
def meta_creatives(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/meta/creatives/"""
    channel = _get_user_channel(request, channel_id)
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.list_creatives())


@login_required
@require_GET
def meta_campaign_insights(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/meta/insights/?campaign_id=X&days=30"""
    channel = _get_user_channel(request, channel_id)
    campaign_id = request.GET.get("campaign_id")
    days = int(request.GET.get("days", 30))
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.get_campaign_insights(campaign_id=campaign_id, days=days))


@login_required
@require_GET
def meta_ad_set_insights(request, channel_id: int) -> JsonResponse:
    """GET /api/channels/<channel_id>/meta/ad-set-insights/?ad_set_id=X&days=30"""
    channel = _get_user_channel(request, channel_id)
    ad_set_id = request.GET.get("ad_set_id", "")
    days = int(request.GET.get("days", 30))
    mgr = _get_meta_manager(channel)
    return JsonResponse(mgr.get_ad_set_insights(ad_set_id=ad_set_id, days=days))
