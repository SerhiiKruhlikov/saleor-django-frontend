# categories/webhooks.py
from .services.categories import invalidate_category_cache


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
    invalidate_category_cache()
    # Logging can stay here or be moved to a separate utility
    print(f"Category cache invalidated due to event: {event_type}")
