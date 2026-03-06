"""Channels URL configuration — Channel CRUD, OAuth, and Google Ads API proxy."""
from django.urls import path

from . import views

app_name = "channels"

urlpatterns = [
    # ── Channel CRUD ─────────────────────────────────────────
    path("project/<int:project_id>/add/", views.channel_add, name="channel_add"),
    path("<int:channel_id>/credentials/", views.channel_credentials, name="channel_credentials"),
    path("<int:channel_id>/delete/", views.channel_delete, name="channel_delete"),

    # ── Google Ads OAuth (channel-scoped) ────────────────────
    path("<int:channel_id>/oauth/google-ads/start/", views.google_ads_oauth_start, name="google_ads_oauth_start"),
    path("<int:channel_id>/oauth/google-ads/exchange/", views.google_ads_oauth_exchange, name="google_ads_oauth_exchange"),
    path("<int:channel_id>/oauth/google-ads/test/", views.google_ads_test_connection, name="google_ads_test_connection"),

    # ── Google Ads API Proxy (channel-scoped) ────────────────
    path("<int:channel_id>/ads/account/", views.ads_account_info, name="ads_account"),
    path("<int:channel_id>/ads/campaigns/", views.ads_campaigns, name="ads_campaigns"),
    path("<int:channel_id>/ads/campaigns/create/", views.ads_create_campaign, name="ads_create_campaign"),
    path("<int:channel_id>/ads/campaigns/status/", views.ads_update_campaign_status, name="ads_update_status"),
    path("<int:channel_id>/ads/campaigns/budget/", views.ads_update_budget, name="ads_update_budget"),
    path("<int:channel_id>/ads/campaigns/<str:campaign_id>/ad-groups/", views.ads_ad_groups, name="ads_ad_groups"),
    path("<int:channel_id>/ads/campaigns/<str:campaign_id>/ad-groups/create/", views.ads_create_ad_group, name="ads_create_ad_group"),
    path("<int:channel_id>/ads/ad-groups/<str:ad_group_id>/keywords/", views.ads_add_keywords, name="ads_add_keywords"),
    path("<int:channel_id>/ads/ad-groups/<str:ad_group_id>/rsa/", views.ads_create_rsa, name="ads_create_rsa"),
    path("<int:channel_id>/ads/conversions/", views.ads_conversions, name="ads_conversions"),
    path("<int:channel_id>/ads/conversions/create/", views.ads_create_conversion, name="ads_create_conversion"),
    path("<int:channel_id>/ads/performance/", views.ads_campaign_performance, name="ads_performance"),
    path("<int:channel_id>/ads/keyword-performance/", views.ads_keyword_performance, name="ads_keyword_performance"),
]
