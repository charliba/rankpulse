"""Analytics URL configuration."""
from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("<int:site_id>/send-event/", views.send_event, name="send_event"),
    path("<int:site_id>/event-logs/", views.event_logs, name="event_logs"),
    path("<int:site_id>/gsc-summary/", views.gsc_summary, name="gsc_summary"),
]
