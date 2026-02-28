"""Core URL configuration."""
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # Site CRUD
    path("site/add/", views.site_add, name="site_add"),
    path("site/<int:site_id>/", views.site_detail, name="site_detail"),
    path("site/<int:site_id>/edit/", views.site_edit, name="site_edit"),
    path("site/<int:site_id>/delete/", views.site_delete, name="site_delete"),
    path("site/<int:site_id>/integrations/", views.site_integrations, name="site_integrations"),
    # Google Ads OAuth flow
    path("site/<int:site_id>/oauth/google-ads/start/", views.google_ads_oauth_start, name="google_ads_oauth_start"),
    path("site/<int:site_id>/oauth/google-ads/exchange/", views.google_ads_oauth_exchange, name="google_ads_oauth_exchange"),
    path("site/<int:site_id>/oauth/google-ads/test/", views.google_ads_test_connection, name="google_ads_test_connection"),
    # Weekly report
    path("site/<int:site_id>/weekly/", views.weekly_report, name="weekly_report"),
    # GA4 Events
    path("site/<int:site_id>/event/add/", views.event_add, name="event_add"),
    path("site/<int:site_id>/event/<int:event_id>/edit/", views.event_edit, name="event_edit"),
    path("site/<int:site_id>/event/<int:event_id>/delete/", views.event_delete, name="event_delete"),
    # KPI Goals
    path("site/<int:site_id>/kpi/add/", views.kpi_add, name="kpi_add"),
    path("site/<int:site_id>/kpi/<int:kpi_id>/edit/", views.kpi_edit, name="kpi_edit"),
    path("site/<int:site_id>/kpi/<int:kpi_id>/delete/", views.kpi_delete, name="kpi_delete"),
]
