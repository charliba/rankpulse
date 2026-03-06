"""
Trafic Provider — URL Configuration
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core.views import landing_view, privacy_view, register, terms_view

urlpatterns = [
    # Public pages
    path("", landing_view, name="landing"),
    path("privacy/", privacy_view, name="privacy"),
    path("terms/", terms_view, name="terms"),
    # Admin
    path("admin/", admin.site.urls),
    # Auth
    path("login/", auth_views.LoginView.as_view(template_name="pages/auth.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),
    path("register/", register, name="register"),
    # API
    path("api/analytics/", include("apps.analytics.urls", namespace="analytics")),
    path("api/seo/", include("apps.seo.urls", namespace="seo")),
    path("api/content/", include("apps.content.urls", namespace="content")),
    path("api/checklists/", include("apps.checklists.urls", namespace="checklists")),
    # Channels (Google Ads, Meta Ads)
    path("api/channels/", include("apps.channels.urls", namespace="channels")),
    # Chat Aura
    path("chat/", include("apps.chat_support.urls", namespace="chat_support")),
    # Dashboard
    path("", include("apps.core.urls", namespace="core")),
]

# Admin customizations
admin.site.site_header = "RankPulse"
admin.site.site_title = "RankPulse Admin"
admin.site.index_title = "Painel de Administracao de Trafego"
