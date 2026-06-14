# categories/webhooks.py
from django.core.cache import cache
from .services.categories import invalidate_global_category_cache


def handle_category_event(event_type: str, payload: dict):
    """
    Handle Saleor webhook events related to categories.

    Calls :func:`~categories.services.categories.invalidate_category_cache`,
    which **removes every cached key** belonging to categories.  This is
    intentionally broad: a change in one category can affect the full
    tree, parent/child relationships, or counts.  The next request to any
    category service will transparently re-fetch fresh data from Saleor.

    If more granular invalidation is needed in the future, the ``payload``
    argument (which currently contains ``{"category": {"slug": "..."}}``)
    can be used to delete only affected keys.
    """
    slug = payload.get("category", {}).get("slug")

    # 1. Invalidate the specific category page (if slug is known)
    if slug:
        cache.delete(f"category_slug_{slug}")
        print(f"Invalidated cache for category slug: {slug}")

    # 2. Invalidate shared data that depends on any category change
    invalidate_global_category_cache()
    print(f"Global category cache invalidated due to event: {event_type}")
