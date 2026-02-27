"""
Trafic Provider — URL Configuration
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
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
