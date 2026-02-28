"""Analytics URL configuration — GA4, GSC, GA4 Admin, Google Ads endpoints."""
from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    # ── GA4 Measurement Protocol ────────────────────────────
    path("<int:site_id>/send-event/", views.send_event, name="send_event"),
    path("<int:site_id>/event-logs/", views.event_logs, name="event_logs"),

    # ── GSC Performance (from DB) ───────────────────────────
    path("<int:site_id>/gsc-summary/", views.gsc_summary, name="gsc_summary"),

    # ── GA4 Data API (Reporting) ────────────────────────────
    path("<int:site_id>/ga4-organic/", views.ga4_organic_traffic, name="ga4_organic"),
    path("<int:site_id>/ga4-conversions/", views.ga4_conversions, name="ga4_conversions"),
    path("<int:site_id>/ga4-pages/", views.ga4_top_pages, name="ga4_pages"),
    path("<int:site_id>/ga4-sources/", views.ga4_traffic_sources, name="ga4_sources"),

    # ── GA4 Admin API (Key Events) ─────────────────────────
    path("<int:site_id>/key-events/", views.ga4_key_events, name="key_events"),
    path("<int:site_id>/key-events/create/", views.ga4_create_key_event, name="key_events_create"),
    path("<int:site_id>/key-events/delete/", views.ga4_delete_key_event, name="key_events_delete"),
    path("<int:site_id>/key-events/mark-beezle/", views.ga4_mark_beezle_events, name="key_events_mark_beezle"),

    # ── GSC Sitemap Management ──────────────────────────────
    path("<int:site_id>/sitemaps/", views.gsc_sitemaps, name="sitemaps"),
    path("<int:site_id>/sitemaps/submit/", views.gsc_submit_sitemap, name="sitemaps_submit"),
    path("<int:site_id>/sitemaps/delete/", views.gsc_delete_sitemap, name="sitemaps_delete"),

    # ── GSC URL Indexing ────────────────────────────────────
    path("<int:site_id>/indexing/submit/", views.gsc_submit_url, name="indexing_submit"),
    path("<int:site_id>/indexing/batch/", views.gsc_batch_submit_urls, name="indexing_batch"),
    path("<int:site_id>/indexing/remove/", views.gsc_remove_url, name="indexing_remove"),

    # ── GSC URL Inspection ──────────────────────────────────
    path("<int:site_id>/inspect/", views.gsc_inspect_url, name="inspect_url"),
    path("<int:site_id>/inspect/batch/", views.gsc_batch_inspect, name="inspect_batch"),

    # ── Google Ads (account-level, no site_id) ──────────────
    path("ads/account/", views.ads_account_info, name="ads_account"),
    path("ads/campaigns/", views.ads_campaigns, name="ads_campaigns"),
    path("ads/campaigns/create/", views.ads_create_campaign, name="ads_create_campaign"),
    path("ads/campaigns/status/", views.ads_update_campaign_status, name="ads_update_status"),
    path("ads/campaigns/budget/", views.ads_update_budget, name="ads_update_budget"),
    path("ads/campaigns/<str:campaign_id>/ad-groups/", views.ads_ad_groups, name="ads_ad_groups"),
    path("ads/campaigns/<str:campaign_id>/ad-groups/create/", views.ads_create_ad_group, name="ads_create_ad_group"),
    path("ads/ad-groups/<str:ad_group_id>/keywords/", views.ads_add_keywords, name="ads_add_keywords"),
    path("ads/ad-groups/<str:ad_group_id>/rsa/", views.ads_create_rsa, name="ads_create_rsa"),
    path("ads/conversions/", views.ads_conversions, name="ads_conversions"),
    path("ads/conversions/create/", views.ads_create_conversion, name="ads_create_conversion"),
    path("ads/performance/", views.ads_campaign_performance, name="ads_performance"),
    path("ads/keyword-performance/", views.ads_keyword_performance, name="ads_keyword_performance"),
    path("ads/setup-beezle/", views.ads_setup_beezle, name="ads_setup_beezle"),
]
