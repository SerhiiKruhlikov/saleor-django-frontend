# products/webhooks.py
import logging
from django.core.cache import cache

from categories.services.categories import invalidate_global_category_cache
from products.services.products import invalidate_product_cache_by_slug, invalidate_product_category_cache, \
    invalidate_all_product_cache
from router.services import invalidate_router_cache

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


def _extract_category_slug(payload: dict) -> str | None:
    product = payload.get("product")
    if isinstance(product, dict):
        category = product.get("category")
        if isinstance(category, dict) and category.get("slug"):
            return category["slug"]
    return None


def handle_product_event(event_type: str, payload: dict):
    """
    Handle Saleor webhook events related to products.

    Invalidates:
    - the product detail page
    - the router cache for the slug
    - all filter/attribute caches for the product's category (if known)
    """
    slug = _extract_product_slug(payload)
    category_slug = _extract_category_slug(payload)

    if slug:
        invalidate_product_cache_by_slug(slug)
        invalidate_router_cache(slug)
        logger.info("Invalidated cache for product slug=%s due to event: %s", slug, event_type)

    if category_slug:
        invalidate_product_category_cache(category_slug)
        logger.info("Invalidated product category cache for %s due to event: %s", category_slug, event_type)

    if not slug and not category_slug:
        logger.warning(
            "Product webhook without usable slug. event_type=%s, payload=%s",
            event_type, payload,
        )


def handle_promotion_event(event_type: str, payload: dict):
    """
    Handle Saleor webhook events related to promotions.

    Invalidates **all** product and category caches because promotion
    changes can affect prices across the entire catalogue.
    """
    logger.info("Promotion event received: %s", event_type)

    # Сбрасываем кеш всех товаров (цены могли измениться)
    invalidate_all_product_cache()

    # Сбрасываем кеш категорий (меню и фильтры могли измениться)
    invalidate_global_category_cache()

    logger.info("All product and category caches invalidated due to event: %s", event_type)
