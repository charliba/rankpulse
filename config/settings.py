"""
Trafic Provider — Django Settings

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
    "corsheaders",
    # Trafic Provider apps
    "apps.core.apps.CoreConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.seo.apps.SeoConfig",
    "apps.content.apps.ContentConfig",
    "apps.checklists.apps.ChecklistsConfig",
    "apps.chat_support.apps.ChatSupportConfig",
]

# ─── Middleware ─────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
            "NAME": os.getenv("DB_NAME", "trafic_provider"),
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

# ─── Static Files ─────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ─── Default PK ───────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Auth / Login ────────────────────────────────────
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# ─── REST Framework ───────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# ─── CORS ─────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ─── Google Analytics 4 ──────────────────────────────
GA4_MEASUREMENT_ID = os.getenv("GA4_MEASUREMENT_ID", "")
GA4_API_SECRET = os.getenv("GA4_API_SECRET", "")
GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")
GA4_SERVICE_ACCOUNT_KEY_PATH = os.getenv("GA4_SERVICE_ACCOUNT_KEY_PATH", "")

# ─── Google Search Console ───────────────────────────
GSC_SERVICE_ACCOUNT_KEY_PATH = os.getenv("GSC_SERVICE_ACCOUNT_KEY_PATH", "")
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "")

# ─── OpenAI ──────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# ─── App Identity ────────────────────────────────────
APP_NAME = os.getenv("APP_NAME", "RankPulse")
APP_DOMAIN = os.getenv("APP_DOMAIN", "rankpulse.cloud")
APP_URL = os.getenv("APP_URL", "https://rankpulse.cloud")

# ─── Default Target Site (Beezle) ────────────────────
SITE_NAME = os.getenv("SITE_NAME", "Beezle")
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "beezle.io")
SITE_URL = os.getenv("SITE_URL", "https://beezle.io")

# ─── Production Security ─────────────────────────────
# These settings are ONLY applied when DEBUG=False (production).
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31_536_000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    CSRF_TRUSTED_ORIGINS = [
        f"https://{APP_DOMAIN}",
        f"https://www.{APP_DOMAIN}",
    ]

# ─── Gunicorn / Deploy ──────────────────────────────
GUNICORN_PORT = int(os.getenv("GUNICORN_PORT", "8002"))

# ─── Logging ─────────────────────────────────────────
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
            "filename": BASE_DIR / "logs" / "trafic_provider.log",
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
