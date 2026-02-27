"""SEO URL configuration."""
from django.urls import path

from . import views

app_name = "seo"

urlpatterns = [
    path("<int:site_id>/audit/", views.run_audit, name="run_audit"),
    path("<int:site_id>/audits/", views.audit_history, name="audit_history"),
    path("<int:site_id>/keywords/", views.keywords, name="keywords"),
]
