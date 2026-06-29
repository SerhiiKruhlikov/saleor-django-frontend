# categories/webhooks.py
import logging
from django.conf import settings
from django.core.cache import cache
from .services.categories import invalidate_category_cache
from router.services import invalidate_router_cache

logger = logging.getLogger(__name__)


def handle_category_event(event_type: str, payload: dict):
    """
    Handle Saleor webhook events related to categories.

    Invalidates the specific category page cache, shared category caches,
    and the router cache for the affected slug.
    """
    slug = payload.get("category", {}).get("slug")

    # 1. Invalidate the specific category page
    if slug:
        for lang_code, _ in settings.LANGUAGES:
            cache.delete(f"categories:{lang_code}:{slug}")
        invalidate_router_cache(slug)
        logger.info("Invalidated cache for category slug=%s", slug)

    # 2. Invalidate shared category data
    invalidate_category_cache()
    logger.info("Global category cache invalidated due to event: %s", event_type)
