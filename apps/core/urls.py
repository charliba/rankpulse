"""Core URL configuration."""
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    # Project CRUD
    path("project/add/", views.project_add, name="project_add"),
    path("project/<int:project_id>/", views.project_detail, name="project_detail"),
    path("project/<int:project_id>/onboarding/", views.project_onboarding, name="project_onboarding"),
    path("project/<int:project_id>/edit/", views.project_edit, name="project_edit"),
    path("project/<int:project_id>/delete/", views.project_delete, name="project_delete"),
    # Project sub-pages
    path("project/<int:project_id>/dashboard/", views.project_dashboard, name="project_dashboard"),
    path("project/<int:project_id>/sources/", views.project_sources, name="project_sources"),
    path("project/<int:project_id>/campaigns/", views.project_campaigns, name="project_campaigns"),
    path("project/<int:project_id>/optimizer/", views.project_optimizer, name="project_optimizer"),
    path("project/<int:project_id>/alerts/", views.project_alerts, name="project_alerts"),
    path("project/<int:project_id>/settings/", views.project_settings, name="project_settings"),
    # API endpoints for async dashboard data
    path("api/project/<int:project_id>/organic-data/", views.api_organic_data, name="api_organic_data"),
    path("api/project/<int:project_id>/ads-data/", views.api_ads_data, name="api_ads_data"),
    path("api/project/<int:project_id>/meta-data/", views.api_meta_data, name="api_meta_data"),
    # API endpoints for campaign tables
    path("api/project/<int:project_id>/campaigns-google/", views.api_campaigns_google, name="api_campaigns_google"),
    path("api/project/<int:project_id>/campaigns-meta/", views.api_campaigns_meta, name="api_campaigns_meta"),
    path("api/project/<int:project_id>/campaigns/<str:campaign_id>/ad-groups/", views.api_campaign_ad_groups, name="api_campaign_ad_groups"),
    path("api/project/<int:project_id>/ad-groups/<str:ad_group_id>/ads/", views.api_ad_group_ads, name="api_ad_group_ads"),
    path("api/project/<int:project_id>/campaigns/update-budget/", views.api_campaign_update_budget, name="api_campaign_update_budget"),
    path("api/project/<int:project_id>/campaigns-meta/<str:campaign_id>/ad-sets/", views.api_campaign_ad_sets_meta, name="api_campaign_ad_sets_meta"),
    path("api/project/<int:project_id>/campaigns-meta/update-budget/", views.api_campaign_update_budget_meta, name="api_campaign_update_budget_meta"),
    # Alert CRUD
    path("project/<int:project_id>/alerts/add/", views.alert_add, name="alert_add"),
    path("project/<int:project_id>/alerts/<int:alert_id>/edit/", views.alert_edit, name="alert_edit"),
    path("project/<int:project_id>/alerts/<int:alert_id>/delete/", views.alert_delete, name="alert_delete"),
    path("project/<int:project_id>/alerts/mark-read/", views.alert_mark_read, name="alert_mark_read"),
    path("api/project/<int:project_id>/alert-events/", views.api_alert_events, name="api_alert_events"),
    # Export
    path("project/<int:project_id>/export/campaigns/", views.export_campaigns_csv, name="export_campaigns_csv"),
    path("project/<int:project_id>/export/report/", views.export_report_html, name="export_report_html"),
    # AI Audit
    path("project/<int:project_id>/audit/", views.project_audit, name="project_audit"),
    path("project/<int:project_id>/audit/parameters/", views.audit_parameters, name="audit_parameters"),
    path("project/<int:project_id>/audit/run/", views.audit_run, name="audit_run"),
    path("project/<int:project_id>/audit/status/", views.audit_status, name="audit_status"),
    path("project/<int:project_id>/audit/apply/<int:rec_id>/", views.audit_apply, name="audit_apply"),
    path("project/<int:project_id>/audit/apply-all/", views.audit_apply_all, name="audit_apply_all"),
    path("project/<int:project_id>/audit/dismiss/<int:rec_id>/", views.audit_dismiss, name="audit_dismiss"),
    path("project/<int:project_id>/audit/brand-refresh/", views.brand_intel_refresh, name="brand_intel_refresh"),
    # AI Knowledge Base
    path("project/<int:project_id>/ai-knowledge-base/", views.ai_knowledge_base, name="ai_knowledge_base"),
    path("project/<int:project_id>/ai-knowledge-base/edit-note/<int:note_id>/", views.knowledge_base_edit_note, name="knowledge_base_edit_note"),
    path("project/<int:project_id>/ai-knowledge-base/delete-note/<int:note_id>/", views.knowledge_base_delete_note, name="knowledge_base_delete_note"),
    path("project/<int:project_id>/ai-knowledge-base/recompile/", views.knowledge_base_recompile, name="knowledge_base_recompile"),
    # Audit AJAX endpoints
    path("project/<int:project_id>/audit/preview/<int:rec_id>/", views.audit_preview, name="audit_preview"),
    path("project/<int:project_id>/audit/apply-ajax/<int:rec_id>/", views.audit_apply_ajax, name="audit_apply_ajax"),
    path("project/<int:project_id>/audit/verify/<int:rec_id>/", views.audit_verify, name="audit_verify"),
    path("project/<int:project_id>/audit/note/<int:rec_id>/", views.audit_add_note, name="audit_add_note"),
    # AI Provider Settings
    path("project/<int:project_id>/ai-settings/", views.ai_settings, name="ai_settings"),
    path("project/<int:project_id>/ai-settings/save/", views.ai_provider_save, name="ai_provider_save"),
    path("project/<int:project_id>/ai-settings/<int:provider_id>/delete/", views.ai_provider_delete, name="ai_provider_delete"),
    path("project/<int:project_id>/ai-settings/test/", views.ai_provider_test, name="ai_provider_test"),
    # Site CRUD (scoped to project)
    path("project/<int:project_id>/site/add/", views.site_add, name="site_add"),
    path("site/<int:site_id>/", views.site_detail, name="site_detail"),
    path("site/<int:site_id>/edit/", views.site_edit, name="site_edit"),
    path("site/<int:site_id>/delete/", views.site_delete, name="site_delete"),
    path("site/<int:site_id>/integrations/", views.site_integrations, name="site_integrations"),
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
    # Google OAuth (GA4 + GSC)
    path("site/<int:site_id>/oauth/google/start/", views.google_oauth_start, name="google_oauth_start"),
    path("integrations/oauth/google/callback/", views.google_oauth_callback, name="google_oauth_callback"),
    path("site/<int:site_id>/oauth/google/select-property/", views.google_select_property, name="google_select_property"),
    path("site/<int:site_id>/oauth/google/select-gsc/", views.google_select_gsc_site, name="google_select_gsc_site"),
    path("site/<int:site_id>/oauth/google/disconnect/", views.google_disconnect, name="google_disconnect"),
    # Developer tools (staff-only) — legacy
    path("admin-dev/errors/", views.error_dashboard, name="error_dashboard"),
    path("admin-dev/errors/<int:error_id>/resolve/", views.error_resolve, name="error_resolve"),
    path("admin-dev/errors/<int:error_id>/notes/", views.error_update_notes, name="error_update_notes"),
    # Admin Dashboard (superuser)
    path("admin-dev/", views.admin_overview, name="admin_overview"),
    path("admin-dev/users/", views.admin_users, name="admin_users"),
    path("admin-dev/users/<int:user_id>/toggle/", views.admin_user_toggle, name="admin_user_toggle"),
    path("admin-dev/users/<int:user_id>/staff-toggle/", views.admin_user_staff_toggle, name="admin_user_staff_toggle"),
    path("admin-dev/projects/", views.admin_projects, name="admin_projects"),
    path("admin-dev/audits/", views.admin_audits, name="admin_audits"),
    path("admin-dev/error-logs/", views.admin_errors, name="admin_errors"),
    path("admin-dev/error-logs/<int:error_id>/resolve/", views.admin_error_resolve, name="admin_error_resolve"),
    path("admin-dev/error-logs/<int:error_id>/notes/", views.admin_error_notes, name="admin_error_notes"),
    path("admin-dev/system/", views.admin_system, name="admin_system"),
]
