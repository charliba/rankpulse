"""Checklists URL configuration."""
from django.urls import path

from . import views

app_name = "checklists"

urlpatterns = [
    path("<int:site_id>/", views.list_checklists, name="list"),
    path("<int:site_id>/create/", views.create_checklist, name="create"),
    path("<int:site_id>/toggle/", views.toggle_item, name="toggle"),
    path("<int:site_id>/<int:checklist_id>/", views.checklist_detail, name="detail"),
]
