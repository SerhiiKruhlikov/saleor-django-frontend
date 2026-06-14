# tests/conftest.py
import os
import pytest
import django
from django.core.cache import cache


def pytest_configure():
    """Set up Django settings before any tests run."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
    django.setup()


@pytest.fixture(autouse=True)
def use_locmem_cache_and_clear(settings):
    """Use LocMemCache and clear the cache before each test."""
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
    cache.clear()
