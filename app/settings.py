# app/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-9q4hlfi#4e9uz6o$c*o!39#ew7r=_ltu*)3(tl5=h5d!--7me6'
DEBUG = True
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    'unlumbering-ling-whiny.ngrok-free.dev',
    '.ngrok-free.dev',
    'host.docker.internal',
]
CSRF_TRUSTED_ORIGINS = [
    'https://unlumbering-ling-whiny.ngrok-free.dev',
    'https://*.ngrok-free.dev',
]

INSTALLED_APPS = [
    'shop',
    'categories',
    'products',
    'compare',
    'basket',
    'orders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shop.context_processors.main_menu',
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = "uk"
LANGUAGES = [
    ("uk", "Ukraine"),
    ("en", "English"),
    ("ru", "Russian"),
]
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = [
    BASE_DIR / "locale",
]

STATICFILES_DIRS = [
    BASE_DIR / "assets",
]
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# FRONTEND SETTINGS
LOCALSTORAGE_PREFIX = "sdf"


# SALEOR
SALEOR_API_URL = os.environ.get("SALEOR_API_URL", "")
SALEOR_API_EMAIL = os.environ.get("SALEOR_API_EMAIL", "")
SALEOR_API_PASSWORD = os.environ.get("SALEOR_API_PASSWORD", "")
SALEOR_WEBHOOK_SECRET = os.environ.get("SALEOR_WEBHOOK_SECRET", "")
SALEOR_CHANNEL = os.environ.get("SALEOR_CHANNEL", "uk-store")
SALEOR_DEFAULT_CURRENCY = os.environ.get("SALEOR_DEFAULT_CURRENCY", "UAH")
SALEOR_PAGINATION_PRODUCTS_PER_PAGE = int(os.environ.get("SALEOR_PAGINATION_PRODUCTS_PER_PAGE", 12))
SALEOR_RECONNECT_INVALIDATION_ENABLED = True


# SPHINX
DOCS = True


# REDIS
# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1"),
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#         },
#         "KEY_PREFIX": "test_techpro_dev"
#     }
# }
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "test_graphql"
    }
}


# =============================================================================
# Cache Time-to-Live Settings (in seconds)
# =============================================================================
# These values control how long data lives in the Redis cache.
# Once a TTL expires, the corresponding data is automatically re-fetched
# from Saleor.
#
# Dictionary keys match the service functions:
#   FULL_TREE            – get_full_tree()           (full category tree)
#   CATEGORY_COUNT       – get_category_count()      (total number of categories)
#   ALL_CATEGORIES       – get_all_categories()      (flat list of categories)
#   CATEGORY_BY_SLUG     – get_category_by_slug()    (single category by slug)
#   PRODUCT_BY_SLUG      – get_product_by_slug()     (single product – later)
#   PRODUCTS_BY_CATEGORY – get_products_by_category()(products of a category – later)
#
# Values can be overridden via .env or a separate settings file.
# -----------------------------------------------------------------------------
CACHE_TIMEOUTS = {
    'FULL_TREE': 3600,              # 1 hour
    'CATEGORY_COUNT': 600,          # 10 minutes
    'ALL_CATEGORIES': 600,          # 10 minutes
    'CATEGORY_BY_SLUG': 1800,       # 30 minutes
    'PRODUCT_BY_SLUG': 1800,
    'PRODUCTS_BY_CATEGORY': 600,
    'ROUTER_SLUG_TYPE': 86400,      # 24 hours – how long a slug type is cached
    'COMPARE_CACHE_TTL': 86400,
    'BASKET_CACHE_TTL': 864000,
}


# =========================
# LOGGING
# =========================
LOG_DIR = BASE_DIR / "logs"
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "django.log",
            "formatter": "simple",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "gateway": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "shop": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "categories": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "products": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "webhooks": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
