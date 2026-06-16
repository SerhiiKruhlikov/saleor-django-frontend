# products/services/products.py
import json
import logging

from django.conf import settings
from django.core.cache import cache

from gateway.saleor.client import safe_execute_query, SaleorUnavailable
from gateway.saleor.loader import load_query

logger = logging.getLogger(__name__)

APP_NAME = "products"

# ----------------------------------------------------------------------
# Cache timeouts from settings (with sensible defaults)
# ----------------------------------------------------------------------
CACHE_TIMEOUTS = getattr(settings, "CACHE_TIMEOUTS", {})

TIMEOUT_PRODUCT_BY_SLUG = CACHE_TIMEOUTS.get("PRODUCT_BY_SLUG", 1800)
TIMEOUT_PRODUCTS_BY_CATEGORY = CACHE_TIMEOUTS.get("PRODUCTS_BY_CATEGORY", 600)
TIMEOUT_NONE = 60  # Short TTL for caching “not found” results


def get_product_by_slug(slug: str, language: str | None = None) -> dict | None:
    """
    Return a single product by its slug (cached).

    If Saleor returns ``null`` for the slug, ``None`` is returned and
    **cached with a short TTL** to avoid repeated queries.
    If Saleor is unreachable, ``None`` is returned **without caching**,
    so the next request can retry.

    Args:
        slug: URL identifier of the product.
        language: Language code for cache key prefix.  Defaults to
            ``settings.LANGUAGE_CODE`` when ``None``.

    Returns:
        Product dictionary, or ``None`` if the product is not found
        or an error occurs.
    """
    if language is None:
        language = settings.LANGUAGE_CODE

    cache_key = f"products:{language}:{slug}"
    product = cache.get(cache_key)

    if product is not None:
        return product

    try:
        query = load_query(APP_NAME, "queries/product_by_slug.graphql")
        variables = {"slug": slug}
        data = safe_execute_query(query, variables)
        if data is None:
            # Product not found – cache the None result briefly
            cache.set(cache_key, None, timeout=TIMEOUT_NONE)
            return None

        product = data.get("product")
        if product is not None:
            if product.get("description"):
                product["description"] = editorjs_to_html(product["description"])
            cache.set(cache_key, product, timeout=TIMEOUT_PRODUCT_BY_SLUG)
        else:
            cache.set(cache_key, None, timeout=TIMEOUT_NONE)

        return product

    except SaleorUnavailable:
        # Do not cache on error – allow a retry on the next request
        logger.warning("Saleor unavailable while fetching product slug=%s", slug)
        return None


def editorjs_to_html(description_json) -> str:
    """
    Convert Editor.js JSON description into safe HTML.

    Supports ``paragraph`` and ``header`` blocks.  Returns the original
    string if it is not valid JSON.
    """
    try:
        data = json.loads(description_json)
    except (json.JSONDecodeError, TypeError):
        return description_json or ""

    blocks = data.get("blocks", [])
    html_parts = []

    for block in blocks:
        block_type = block.get("type", "")
        block_data = block.get("data", {})

        if block_type == "paragraph":
            text = block_data.get("text", "")
            html_parts.append(f"<p>{text}</p>")

        elif block_type == "header":
            text = block_data.get("text", "")
            level = block_data.get("level", 2)
            level = max(1, min(level, 6))
            html_parts.append(f"<h{level}>{text}</h{level}>")

    return "\n".join(html_parts)


def get_products_by_category(
    slug: str,
    first: int = 12,
    after: str | None = None,
    language: str | None = None,
) -> dict:
    """
    Return paginated products for a given category slug (cached).

    Args:
        slug: Category slug.
        first: Number of products per page.
        after: Cursor for the next page (``None`` for the first page).
        language: Language code for cache key.  Defaults to
            ``settings.LANGUAGE_CODE``.

    Returns:
        Dictionary with ``edges`` (list of product nodes), ``page_info``
        (hasNextPage, endCursor), and ``total_count``.  Returns an empty
        result on error.
    """
    if language is None:
        language = settings.LANGUAGE_CODE

    cache_key = f"products:by_category:{language}:{slug}:{first}:{after or 'first'}"
    result = cache.get(cache_key)
    if result is not None:
        return result

    try:
        query = load_query(APP_NAME, "queries/products_by_category.graphql")
        variables = {
            "slug": slug,
            "first": first,
            "after": after,
            "channel": settings.SALEOR_CHANNEL,
        }
        data = safe_execute_query(query, variables)
        if data is None:
            return {"edges": [], "page_info": {}, "total_count": 0}

        category = data.get("category")
        if not category:
            return {"edges": [], "page_info": {}, "total_count": 0}

        products = category.get("products", {})
        result = {
            "edges": products.get("edges", []),
            "page_info": products.get("pageInfo", {}),
            "total_count": products.get("totalCount", 0),
        }
        if result["edges"]:
            cache.set(cache_key, result, timeout=TIMEOUT_PRODUCTS_BY_CATEGORY)
        return result

    except SaleorUnavailable:
        logger.warning("Saleor unavailable while fetching products for category slug=%s", slug)
        return {"edges": [], "page_info": {}, "total_count": 0}


# ----------------------------------------------------------------------
# Cache invalidation
# ----------------------------------------------------------------------

def invalidate_product_cache_by_slug(slug: str):
    """
    Remove the cached entry for a single product in all languages.

    Should be called from the product webhook handler whenever a product
    is created, updated, or deleted.
    """
    for lang_code, _ in settings.LANGUAGES:
        cache.delete(f"products:{lang_code}:{slug}")
    logger.info("Invalidated cache for product slug=%s", slug)
