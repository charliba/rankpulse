"""URLs do chat de suporte Aura."""
from django.urls import path

from . import views

app_name = "chat_support"

urlpatterns = [
    path("send/", views.send_message, name="send_message"),
    path("messages/", views.get_messages, name="get_messages"),
    path("close/", views.close_chat, name="close_chat"),
]
