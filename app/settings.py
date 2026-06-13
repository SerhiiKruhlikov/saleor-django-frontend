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
]
CSRF_TRUSTED_ORIGINS = [
    'https://unlumbering-ling-whiny.ngrok-free.dev',
    'https://*.ngrok-free.dev'
]

INSTALLED_APPS = [
    'shop',
    'categories',
    'products',
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

STATICFILES_DIRS = [
    BASE_DIR / "assets",
]
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# SALEOR
SALEOR_API_URL = os.environ.get("SALEOR_API_URL", "")
SALEOR_API_EMAIL = os.environ.get("SALEOR_API_EMAIL", "")
SALEOR_API_PASSWORD = os.environ.get("SALEOR_API_PASSWORD", "")
SALEOR_WEBHOOK_SECRET = os.environ.get("SALEOR_WEBHOOK_SECRET", "")


# SPHINX
DOCS = True


# REDIS
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "test_techpro_dev"
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
    'FULL_TREE': 3600,            # 1 hour
    'CATEGORY_COUNT': 600,        # 10 minutes
    'ALL_CATEGORIES': 600,        # 10 minutes
    'CATEGORY_BY_SLUG': 1800,     # 30 minutes
    # For products (to be added later)
    'PRODUCT_BY_SLUG': 1800,
    'PRODUCTS_BY_CATEGORY': 600,
}