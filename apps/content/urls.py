"""Content URL configuration."""
from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    # Legacy API endpoints (site-scoped)
    path("<int:site_id>/generate/", views.generate, name="generate"),
    path("<int:site_id>/topics/", views.topics, name="topics"),
    path("<int:site_id>/posts/", views.posts, name="posts"),

    # Social Content (project-scoped, HTML views)
    path("social/<int:project_id>/", views.social_dashboard, name="social_dashboard"),
    path("social/<int:project_id>/generate/", views.social_generate, name="social_generate"),
    path("social/<int:project_id>/post/<int:post_id>/", views.social_post_detail, name="social_post_detail"),
]
