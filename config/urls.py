"""
Trafic Provider — URL Configuration
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Auth
    path("login/", auth_views.LoginView.as_view(template_name="pages/auth.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),
    # API
    path("api/analytics/", include("apps.analytics.urls", namespace="analytics")),
    path("api/seo/", include("apps.seo.urls", namespace="seo")),
    path("api/content/", include("apps.content.urls", namespace="content")),
    path("api/checklists/", include("apps.checklists.urls", namespace="checklists")),
    # Dashboard
    path("", include("apps.core.urls", namespace="core")),
]

# Admin customizations
admin.site.site_header = "RankPulse"
admin.site.site_title = "RankPulse Admin"
admin.site.index_title = "Painel de Administracao de Trafego"
