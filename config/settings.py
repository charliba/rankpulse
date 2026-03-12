"""
RankPulse — Django Settings

Sistema de administracao de trafego organico e analytics.
Desenvolvido para gerenciar SEO, GA4, conteudo e KPIs de sites web.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── Paths ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ──────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

# ─── Applications ─────────────────────────────────────
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "huey.contrib.djhuey",
    # RankPulse apps
    "apps.core.apps.CoreConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.seo.apps.SeoConfig",
    "apps.content.apps.ContentConfig",
    "apps.checklists.apps.ChecklistsConfig",
    "apps.chat_support.apps.ChatSupportConfig",
    "apps.channels.apps.ChannelsConfig",
    "apps.payments.apps.PaymentsConfig",
]

# ─── Middleware ─────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.ErrorTrackingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.error_count",
                "apps.core.context_processors.app_domain",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─── Database ──────────────────────────────────────────
db_engine = os.getenv("DB_ENGINE", "sqlite3")
if "postgresql" in db_engine:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "rankpulse"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Auth ──────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

# ─── Internationalization ─────────────────────────────
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("pt-br", "Português"),
    ("en", "English"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# ─── Static Files ─────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ─── Media Files ──────────────────────────────────────
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── Default PK ───────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Auth / Login ────────────────────────────────────
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

# ─── REST Framework ───────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "120/minute",
    },
}

# ─── CORS (removido — nenhum projeto que funciona no Safari usa) ─────

# ─── Google Service Account (platform-level) ────────
# One Service Account serves all clients for GA4 + GSC
SERVICE_ACCOUNT_KEY_PATH = os.getenv("SERVICE_ACCOUNT_KEY_PATH", "")
GA4_SERVICE_ACCOUNT_KEY_PATH = os.getenv("GA4_SERVICE_ACCOUNT_KEY_PATH", "") or SERVICE_ACCOUNT_KEY_PATH
GSC_SERVICE_ACCOUNT_KEY_PATH = os.getenv("GSC_SERVICE_ACCOUNT_KEY_PATH", "") or SERVICE_ACCOUNT_KEY_PATH

# Auto-extract client_email from the Service Account JSON
SERVICE_ACCOUNT_EMAIL = ""
if SERVICE_ACCOUNT_KEY_PATH:
    try:
        import json as _json
        with open(SERVICE_ACCOUNT_KEY_PATH) as _f:
            SERVICE_ACCOUNT_EMAIL = _json.load(_f).get("client_email", "")
    except (FileNotFoundError, ValueError, KeyError):
        pass

# ─── Google Analytics 4 ──────────────────────────────
GA4_MEASUREMENT_ID = os.getenv("GA4_MEASUREMENT_ID", "")
GA4_API_SECRET = os.getenv("GA4_API_SECRET", "")
GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")

# ─── Google Search Console ───────────────────────────
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "")

# ── Google Ads (platform-level OAuth app credentials) ─
# These are the OAuth client credentials for the RankPulse app itself.
# Per-channel credentials (customer_id, refresh_token, etc.) are stored
# in ChannelCredential model.
GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")

# ─── OpenAI ──────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# ─── Stripe ──────────────────────────────────────────────
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# ─── Google Gemini ───────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─── Huey Task Queue (SQLite backend — no Redis needed) ──
HUEY = {
    "huey_class": "huey.SqliteHuey",
    "name": "rankpulse",
    "filename": str(BASE_DIR / "huey.db"),
    # immediate=True runs tasks synchronously (safe default).
    # Set HUEY_IMMEDIATE=false after starting `manage.py run_huey` consumer.
    "immediate": os.getenv("HUEY_IMMEDIATE", "true").lower() in ("true", "1", "yes"),
}

# ─── App Identity ────────────────────────────────────
APP_NAME = os.getenv("APP_NAME", "RankPulse")
APP_DOMAIN = os.getenv("APP_DOMAIN", "rankpulse.cloud")
APP_URL = os.getenv("APP_URL", f"https://app.{APP_DOMAIN}")

# ─── Email ───────────────────────────────────────────
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.hostinger.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() in ("true", "1", "yes")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True").lower() in ("true", "1", "yes")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", f"RankPulse <contato@{APP_DOMAIN}>")

# ─── Telegram CEO Bot ───────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("AGENCY_BOT_TOKEN", "")
TELEGRAM_OWNER_CHAT_ID = os.getenv("AGENCY_OWNER_CHAT_ID", "")

# ─── Session & Cookie Config (always applied) ────────
# SESSION_COOKIE_DOMAIN left as None — each subdomain (app., admin.)
# gets its own cookie. Required for Safari ITP compatibility on iOS.
SESSION_COOKIE_NAME = "rp_sid"              # avoid stale cookie conflicts
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True               # site is always HTTPS behind nginx
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_AGE = 1_209_600             # 14 days
SESSION_SAVE_EVERY_REQUEST = True          # refresh session on every request

# ─── Proxy & CSRF (always needed behind nginx) ───────
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    f"https://{APP_DOMAIN}",
    f"https://www.{APP_DOMAIN}",
    f"https://app.{APP_DOMAIN}",
    f"https://admin.{APP_DOMAIN}",
]

# ─── Production Security ─────────────────────────────
# These settings are ONLY applied when DEBUG=False (production).
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31_536_000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

# ─── Gunicorn / Deploy ──────────────────────────────
GUNICORN_PORT = int(os.getenv("GUNICORN_PORT", "8002"))

# ─── Logging ─────────────────────────────────────────
# ====================== CACHE ======================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(BASE_DIR / "cache"),
        "TIMEOUT": 3600,
        "OPTIONS": {"MAX_ENTRIES": 1000},
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "rankpulse.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "apps.analytics": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False},
        "apps.seo": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False},
        "apps.content": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False},
    },
}
