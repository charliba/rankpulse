"""
RankPulse — URL Configuration
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core.views import landing_view, login_view, privacy_view, register, terms_view
from apps.channels.views import meta_oauth_callback, google_ads_oauth_callback
from apps.core.seo_views import robots_txt, sitemap_xml

urlpatterns = [
    # SEO
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
    # Public pages
    path("", landing_view, name="landing"),
    path("privacy/", privacy_view, name="privacy"),
    path("terms/", terms_view, name="terms"),
    # Meta OAuth callback (fixed URL for Facebook redirect)
    path("channels/oauth/meta/callback/", meta_oauth_callback, name="meta_oauth_callback_root"),
    # Google OAuth callback (fixed URL for Google redirect)
    path("channels/oauth/google-ads/callback/", google_ads_oauth_callback, name="google_ads_oauth_callback_root"),
    # Admin
    path("admin/", admin.site.urls),
    # Auth
    path("login/", login_view, name="login"),
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
    # Payments / Stripe
    path("api/", include("apps.payments.urls", namespace="payments")),
    # Dashboard
    path("", include("apps.core.urls", namespace="core")),
]

# Admin customizations
admin.site.site_header = "RankPulse"
admin.site.site_title = "RankPulse Admin"
admin.site.index_title = "Painel de Administracao de Trafego"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
