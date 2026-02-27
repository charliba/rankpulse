"""Content URL configuration."""
from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    path("<int:site_id>/generate/", views.generate, name="generate"),
    path("<int:site_id>/topics/", views.topics, name="topics"),
    path("<int:site_id>/posts/", views.posts, name="posts"),
]
