"""URLs do chat de suporte Aura."""
from django.urls import path

from . import views

app_name = "chat_support"

urlpatterns = [
    path("send/", views.send_message, name="send_message"),
    path("messages/", views.get_messages, name="get_messages"),
    path("close/", views.close_chat, name="close_chat"),
    # Feedback
    path("feedback/submit/", views.submit_feedback, name="submit_feedback"),
    path("feedback/", views.feedback_panel, name="feedback_panel"),
    path("feedback/<int:pk>/update/", views.feedback_update_status, name="feedback_update"),
    path("feedback/<int:pk>/approve/", views.feedback_approve, name="feedback_approve"),
]
