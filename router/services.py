# router/services.py
import logging
from django.core.cache import cache
from django.conf import settings
from gateway.saleor.client import safe_execute_query, SaleorUnavailable
from gateway.saleor.loader import load_query

logger = logging.getLogger(__name__)

APP_NAME = "router"                     # папка, где лежат .graphql запросы
CACHE_TIMEOUTS = getattr(settings, 'CACHE_TIMEOUTS', {})
ROUTER_TTL = CACHE_TIMEOUTS.get('ROUTER_SLUG_TYPE', 86400)


def resolve_slug(slug: str, language: str | None = None) -> str | None:
    """
    Determine the type of entity for a given slug.

    Checks the cache first, then queries Saleor for a product, then for a
    category.  If Saleor is unavailable, returns ``None`` (which will
    result in a friendly error page, not a crash).

    Args:
        slug: URL slug to resolve.
        language: Active language code (used to build the cache key).

    Returns:
        ``"product"``, ``"category"``, or ``None`` if nothing matches or
        Saleor is unreachable.
    """
    if language is None:
        language = settings.LANGUAGE_CODE

    cache_key = f"router:type:{language}:{slug}"
    cached_type = cache.get(cache_key)
    if cached_type in ("product", "category"):
        return cached_type

    # 1. Try product
    try:
        query = load_query(APP_NAME, "queries/resolve_product.graphql")
        data = safe_execute_query(query, {"slug": slug})
        if data and data.get("product"):
            cache.set(cache_key, "product", timeout=ROUTER_TTL)
            return "product"
    except SaleorUnavailable:
        logger.warning("Saleor unavailable while resolving product slug=%s", slug)
        return None

    # 2. Try category
    try:
        query = load_query(APP_NAME, "queries/resolve_category.graphql")
        data = safe_execute_query(query, {"slug": slug})
        if data and data.get("category"):
            cache.set(cache_key, "category", timeout=ROUTER_TTL)
            return "category"
    except SaleorUnavailable:
        logger.warning("Saleor unavailable while resolving category slug=%s", slug)
        return None

    return None


def invalidate_router_cache(slug: str):
    """
    Remove cached router type for the given slug in all languages.

    Call this whenever a product or category is created, updated,
    or deleted, so the router re-evaluates the slug on the next
    request.
    """
    # Удаляем ключи для всех поддерживаемых языков (uk, en, ru)
    for lang_code, _ in settings.LANGUAGES:
        cache.delete(f"router:type:{lang_code}:{slug}")
    logger.info("Router cache invalidated for slug=%s", slug)


def parse_filter_url(path: str) -> dict[str, list[str]] | None:
    """
    Parse a filter URL like /category/filter/attr1-value1-or-value2/attr2-value/
    Returns a dict {attribute_slug: [value_slug, ...]} or None if not a filter URL.
    """
    parts = path.strip('/').split('/')
    try:
        filter_index = parts.index('filter')
    except ValueError:
        return None

    filter_parts = parts[filter_index + 1:]
    if not filter_parts:
        return None

    filters = {}
    for part in filter_parts:
        if not part or '-' not in part:
            continue
        attr_slug, values_str = part.split('-', 1)
        values = values_str.split('-or-') if values_str else []
        if attr_slug and values:
            filters[attr_slug] = values

    return filters if filters else None
