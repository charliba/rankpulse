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
    path("project/<int:project_id>/edit/", views.project_edit, name="project_edit"),
    path("project/<int:project_id>/delete/", views.project_delete, name="project_delete"),
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
]
