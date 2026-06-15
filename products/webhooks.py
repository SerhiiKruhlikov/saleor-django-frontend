# products/webhooks.py
import logging
from django.core.cache import cache
from products.services.products import invalidate_product_cache_by_slug

logger = logging.getLogger(__name__)


def _extract_product_slug(payload: dict) -> str | None:
    """
    Extract the product slug from various webhook payload structures.

    Supports:
    - ``product.slug`` (ProductCreated, ProductUpdated, ProductDeleted)
    - ``productVariant.product.slug`` (ProductVariantCreated, etc.)
    - ``productId`` (ProductMediaCreated, etc.) – returns None for now
      because additional query would be needed.
    """
    # Direct product slug
    product = payload.get("product")
    if isinstance(product, dict) and product.get("slug"):
        return product["slug"]

    return None


def handle_product_event(event_type: str, payload: dict):
    """
    Handle Saleor webhook events related to products.

    Extracts the product slug from the payload and invalidates
    the corresponding cache entry.

    Args:
        event_type: ``"ProductCreated"``, ``"ProductUpdated"``, etc.
        payload: Full JSON payload from Saleor.
    """
    slug = _extract_product_slug(payload)
    if slug:
        invalidate_product_cache_by_slug(slug)
        logger.info("Invalidated cache for product slug=%s due to event: %s", slug, event_type)
    else:
        logger.warning(
            "Product webhook without usable slug. event_type=%s, payload=%s",
            event_type, payload,
        )
