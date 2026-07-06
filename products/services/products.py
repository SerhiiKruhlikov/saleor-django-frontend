# products/services/products.py
import json
import logging

from django.conf import settings
from django.core.cache import cache

from gateway.saleor.client import safe_execute_query, SaleorUnavailable
from gateway.saleor.loader import load_query
from gateway.redis_utils import delete_keys_by_pattern

from collections import defaultdict

logger = logging.getLogger(__name__)

APP_NAME = "products"

# ----------------------------------------------------------------------
# Cache timeouts from settings (with sensible defaults)
# ----------------------------------------------------------------------
CACHE_TIMEOUTS = getattr(settings, "CACHE_TIMEOUTS", {})

TIMEOUT_PRODUCT_BY_SLUG = CACHE_TIMEOUTS.get("PRODUCT_BY_SLUG", 1800)
TIMEOUT_PRODUCTS_BY_CATEGORY = CACHE_TIMEOUTS.get("PRODUCTS_BY_CATEGORY", 600)
TIMEOUT_NONE = 60  # Short TTL for caching “not found” results
TIMEOUT_SNAPSHOT = getattr(settings, 'BASKET_CACHE_TTL', 864000)


def _apply_product_translations(edges: list):
    """
    Replace name (and any other translatable fields) with their translated
    versions for each product, its category, attributes, and attribute values.
    """
    for edge in edges:
        node = edge.get("node", {})
        # --- Товар ---
        _apply_translation(node)

        # --- Категория (для хлебных крошек и ссылок) ---
        category = node.get("category")
        if category:
            _apply_translation(category)

        # --- Атрибуты ---
        for attr in node.get("attributes", []):
            # Сам атрибут
            _apply_translation(attr.get("attribute", {}))
            # Значения атрибута
            for value in attr.get("values", []):
                _apply_translation(value)


def _apply_translation(obj: dict):
    """
    If *obj* contains a ``translation`` dict, copy its contents into *obj*
    (overwriting existing keys).  This makes the translated fields
    directly accessible as obj['name'], obj['description'], etc.
    """
    translation = obj.get("translation")
    if translation:
        for key, val in translation.items():
            if val is not None:          # не перезаписываем None'ами
                obj[key] = val


def _extract_status(edges: list):
    """
    For each product, find the attribute with slug 'status' and store its
    first value as ``product['status']`` (dict with ``name`` and ``slug``).
    If the attribute is missing or empty, ``status`` is set to ``None``.
    """
    for edge in edges:
        node = edge.get("node", {})
        status_value = None
        for attr in node.get("attributes", []):
            if attr.get("attribute", {}).get("slug") == "status":
                values = attr.get("values", [])
                if values:
                    val = values[0]
                    status_value = {
                        "name": val.get("name", ""),
                        "slug": val.get("slug", ""),
                    }
                break
        node["status"] = status_value


def _extract_prices(edges: list):
    for edge in edges:
        node = edge.get("node", {})
        pricing = node.get("pricing", {})
        price_range = pricing.get("priceRange", {})
        undiscounted_range = pricing.get("priceRangeUndiscounted", {})

        new_price = None
        old_price = None

        if price_range:
            start = price_range.get("start", {})
            gross = start.get("gross", {})
            new_price = {
                "amount": gross.get("amount"),
                "currency": gross.get("currency"),
            } if gross.get("amount") is not None else None

        if undiscounted_range:
            start = undiscounted_range.get("start", {})
            gross = start.get("gross", {})
            old_price = {
                "amount": gross.get("amount"),
                "currency": gross.get("currency"),
            } if gross.get("amount") is not None else None

        node["new_price"] = new_price
        node["old_price"] = old_price if old_price != new_price else None


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
        variables = {"slug": slug, "channel": settings.SALEOR_CHANNEL, "lang": language.upper()}
        data = safe_execute_query(query, variables)
        if data is None:
            # Product not found – cache the None result briefly
            cache.set(cache_key, None, timeout=TIMEOUT_NONE)
            return None

        product = data.get("product")
        if product is not None:
            # Преобразуем availableForPurchase в булево
            available = product.get("availableForPurchase")
            product["available_for_purchase"] = bool(available) if available else False

            translation = product.get("translation")
            if translation and translation.get("name"):
                product["name"] = translation["name"]

            # Применяем перевод названия категории
            category = product.get("category")
            if category:
                cat_trans = category.get("translation")
                if cat_trans and cat_trans.get("name"):
                    category["name"] = cat_trans["name"]

            description = None
            if translation and translation.get("description"):
                description = translation["description"]
            elif product.get("description"):
                description = product["description"]
            if description:
                product["description"] = editorjs_to_html(description)

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


def get_products_by_category(slug: str, first: int = 12, after: str | None = None, language: str | None = None) -> dict:
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
            "lang": language.upper(),
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
        _apply_product_translations(result["edges"])
        _extract_status(result["edges"])
        _extract_prices(result["edges"])
        if result["edges"]:
            cache.set(cache_key, result, timeout=TIMEOUT_PRODUCTS_BY_CATEGORY)
        return result

    except SaleorUnavailable:
        logger.warning("Saleor unavailable while fetching products for category slug=%s", slug)
        return {"edges": [], "page_info": {}, "total_count": 0}


def get_category_with_filters(
    slug: str,
    selected_filters: dict[str, list[str]] | None = None,
    first: int = 12,
    after: str | None = None,
    language: str | None = None,
) -> dict:
    if language is None:
        language = settings.LANGUAGE_CODE
    if selected_filters is None:
        selected_filters = {}

    # Build cache key that includes filter state
    filter_part = json.dumps(selected_filters, sort_keys=True) if selected_filters else "all"
    cache_key = f"products:facet:{language}:{slug}:{filter_part}:{first}:{after or 'first'}"
    result = cache.get(cache_key)
    if result is not None:
        return result

    # 1. Get UNFILTERED attribute counts (original, always kept intact)
    unfiltered_attrs = get_category_attributes(
        slug, language=language, selected_filters=None, active_attr=None,
    )

    # If no filter selected, return unfiltered data as-is
    if not selected_filters:
        products = _fetch_products(slug, first, after, language, filter_dict=None)
        if products["total_count"] == 0:
            result = {"filters": None, "products": products}
        else:
            result = {"filters": unfiltered_attrs, "products": products}
        cache.set(cache_key, result, timeout=TIMEOUT_PRODUCTS_BY_CATEGORY)
        return result

    # 2. Get FILTERED products (first page)
    products = _fetch_products(slug, first, after, language, filter_dict=selected_filters)

    # 3. Get ALL filtered products to calculate accurate counts for non‑active attrs
    total_count = products["total_count"]
    all_filtered = _fetch_products(slug, total_count, None, language, filter_dict=selected_filters)
    filtered_attr_counts = _aggregate_attributes(all_filtered["edges"])

    # 4. Determine the active attribute (the only one being filtered)
    active_attr = None
    if len(selected_filters) == 1:
        active_attr = next(iter(selected_filters))

    # 5. Build final filters array
    filters = []
    for attr in unfiltered_attrs:
        attr_slug = attr["slug"]
        selected = selected_filters.get(attr_slug, [])
        new_values = []

        if attr_slug == active_attr:
            for value in attr["values"]:
                new_values.append({
                    "slug": value["slug"],
                    "name": value.get("name", value["slug"]),
                    "count": value["count"],
                    "available": True,
                    "selected": value["slug"] in selected,
                })
        else:
            # Non‑active attributes: use filtered counts, keep names from unfiltered
            filtered_values = filtered_attr_counts.get(attr_slug, {})
            # Build a mapping slug -> name from unfiltered values
            name_map = {v["slug"]: v.get("name", v["slug"]) for v in attr["values"]}
            for value in attr["values"]:
                slug_val = value["slug"]
                cnt = filtered_values.get(slug_val, 0)
                new_values.append({
                    "slug": slug_val,
                    "name": name_map.get(slug_val, slug_val),
                    "count": cnt,
                    "available": cnt > 0,
                    "selected": slug_val in selected,
                })
            new_values.sort(key=lambda v: v["count"], reverse=True)

        filters.append({
            "slug": attr_slug,
            "name": attr["name"],
            "values": new_values,
        })

    result = {"filters": filters, "products": products}
    cache.set(cache_key, result, timeout=TIMEOUT_PRODUCTS_BY_CATEGORY)
    return result


def _aggregate_attributes(edges: list) -> dict[str, dict[str, int]]:
    """Return {attr_slug: {value_slug: count}} from product edges."""
    counts: dict[str, dict[str, int]] = {}
    for edge in edges:
        for attr in edge["node"].get("attributes", []):
            slug = attr["attribute"]["slug"]
            if slug not in counts:
                counts[slug] = defaultdict(int)
            for value in attr["values"]:
                counts[slug][value["slug"]] += 1
    return counts


def _fetch_products(slug, first, after, language, filter_dict):
    try:
        query = load_query(APP_NAME, "queries/products_by_category_with_attributes.graphql")
        variables = {
            "slug": slug,
            "first": first,
            "after": after,
            "channel": settings.SALEOR_CHANNEL,
            "lang": language.upper(),
        }
        if filter_dict:
            attributes_filter = [
                {"slug": attr_slug, "values": values}
                for attr_slug, values in filter_dict.items()
            ]
            variables["filter"] = {"attributes": attributes_filter}

        data = safe_execute_query(query, variables)
        if data:
            category = data.get("category")
            if category:
                pdata = category.get("products", {})
                result = {
                    "edges": pdata.get("edges", []),
                    "page_info": pdata.get("pageInfo", {}),
                    "total_count": pdata.get("totalCount", 0),
                }
                _apply_product_translations(result["edges"])
                _extract_status(result["edges"])
                _extract_prices(result["edges"])
                return result
    except SaleorUnavailable:
        logger.warning("Saleor unavailable while fetching products for slug=%s", slug)
    return {"edges": [], "page_info": {}, "total_count": 0}


def get_category_product_count(slug: str, language: str | None = None) -> int:
    """
    Return the total number of products in a given category (cached).

    Args:
        slug: Category slug.
        language: Language code for cache key.

    Returns:
        Number of products in the category, or 0 on error.
    """
    if language is None:
        language = settings.LANGUAGE_CODE

    cache_key = f"products:count:{language}:{slug}"
    count = cache.get(cache_key)
    if count is not None:
        return count

    try:
        query = load_query(APP_NAME, "queries/products_by_category.graphql")
        variables = {
            "slug": slug,
            "first": 1,
            "after": None,
            "channel": settings.SALEOR_CHANNEL,
            "lang": language.upper(),
        }
        data = safe_execute_query(query, variables)
        if data is None:
            return 0
        count = data.get("category", {}).get("products", {}).get("totalCount", 0)
        cache.set(cache_key, count, timeout=TIMEOUT_PRODUCTS_BY_CATEGORY)
        return count
    except SaleorUnavailable:
        return 0


def get_category_attributes(slug: str, language: str | None = None, selected_filters: dict[str, list[str]] | None = None, active_attr: str | None = None) -> list[dict]:
    """
    Return attribute facets with **unfiltered** counts for all products.
    """
    if language is None:
        language = settings.LANGUAGE_CODE
    if selected_filters is None:
        selected_filters = {}

    cache_key = f"products:attributes:unfiltered:{language}:{slug}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        total = get_category_product_count(slug, language=language)
        if total == 0:
            return []

        query = load_query(APP_NAME, "queries/products_by_category_with_attributes.graphql")
        variables = {
            "slug": slug,
            "first": total,
            "after": None,
            "channel": settings.SALEOR_CHANNEL,
            "lang": language.upper(),
        }
        data = safe_execute_query(query, variables)
        if data is None:
            return []

        products_data = data.get("category", {}).get("products", {})
        edges = products_data.get("edges", [])

        # Collect attribute names and value counts
        attr_names: dict[str, str] = {}
        attr_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        value_names: dict[str, dict[str, str]] = defaultdict(dict)
        for edge in edges:
            for attr in edge["node"].get("attributes", []):
                attr_slug = attr["attribute"]["slug"]
                attr_translation = attr["attribute"].get("translation")
                attr_name = (
                    attr_translation.get("name")
                    if attr_translation and attr_translation.get("name")
                    else attr["attribute"]["name"]
                )
                attr_names[attr_slug] = attr_name
                for value in attr["values"]:
                    val_slug = value["slug"]
                    attr_counts[attr_slug][val_slug] += 1
                    val_translation = value.get("translation")
                    val_name = (
                        val_translation.get("name")
                        if val_translation and val_translation.get("name")
                        else value.get("name", val_slug)
                    )
                    value_names[attr_slug][val_slug] = val_name

        filters = []
        for attr_slug, value_counts in attr_counts.items():
            values_list = []
            for value_slug, count in value_counts.items():
                values_list.append({
                    "slug": value_slug,
                    "name": value_names[attr_slug].get(value_slug, value_slug),
                    "count": count,
                    "available": True,
                    "selected": False,
                })
            values_list.sort(key=lambda v: v["count"], reverse=True)
            filters.append({
                "slug": attr_slug,
                "name": attr_names.get(attr_slug, attr_slug),
                "values": values_list,
            })

        cache.set(cache_key, filters, timeout=TIMEOUT_PRODUCTS_BY_CATEGORY)
        return filters

    except SaleorUnavailable:
        return []


def get_product_snapshot(slug: str, language: str | None = None) -> dict | None:
    """
    Return a lightweight product snapshot for the basket.
    Cached in Redis per language.
    """
    if language is None:
        language = settings.LANGUAGE_CODE

    cache_key = f"products:snapshot:{language}:{slug}"
    snapshot = cache.get(cache_key)
    if snapshot is not None:
        return snapshot

    try:
        query = load_query(APP_NAME, "queries/product_by_slug.graphql")
        variables = {
            "slug": slug,
            "channel": settings.SALEOR_CHANNEL,
            "lang": language.upper(),
        }
        data = safe_execute_query(query, variables)
        if data is None:
            return None

        product = data.get("product")
        if not product:
            return None

        # Применяем перевод названия
        translation = product.get("translation")
        if translation and translation.get("name"):
            product["name"] = translation["name"]

        # Доступность для покупки
        available = product.get("availableForPurchase")
        available_for_purchase = bool(available) if available else False

        # Цена
        pricing = product.get("pricing", {})
        price_range = pricing.get("priceRange", {})
        price_amount = None
        price_currency = None
        if price_range:
            start = price_range.get("start", {}).get("gross", {})
            price_amount = start.get("amount")
            price_currency = start.get("currency")

        variants = product.get("variants", [])
        variant = variants[0] if variants else None
        variant_id = variant["id"] if variant else None
        sku = variant.get("sku") if variant else None

        snapshot = {
            "slug": product["slug"],
            "name": product.get("name", ""),
            "thumbnail": product.get("thumbnail", {}).get("url") if product.get("thumbnail") else None,
            "available_for_purchase": available_for_purchase,
            "price": {
                "amount": price_amount,
                "currency": price_currency,
            },
            "variant_id": variant_id,
            "sku": sku,
        }

        cache.set(cache_key, snapshot, timeout=TIMEOUT_SNAPSHOT)
        return snapshot

    except SaleorUnavailable:
        logger.warning("Saleor unavailable while fetching snapshot for %s", slug)
        return None


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


def invalidate_product_category_cache(category_slug: str):
    """
    Remove all cached filter, attribute and count data for a given category.

    Call this whenever a product inside the category is created, updated
    or deleted.
    """
    for lang_code, _ in settings.LANGUAGES:
        cache.delete(f"products:count:{lang_code}:{category_slug}")
        cache.delete_pattern(f"products:attributes:unfiltered:{lang_code}:{category_slug}")
        cache.delete_pattern(f"products:facet:{lang_code}:{category_slug}:*")
        cache.delete_pattern(f"products:by_category:{lang_code}:{category_slug}:*")
    logger.info("Invalidated product caches for category slug=%s", category_slug)


def invalidate_basket_snapshots(slug: str):
    """
    Deletes all cached snapshots for this product in all languages,
    respecting the cache key prefix.
    """
    prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
    if prefix:
        pattern = f"{prefix}:*products:snapshot:*:{slug}"
    else:
        pattern = f"*products:snapshot:*:{slug}"
    deleted = delete_keys_by_pattern(pattern)
    logger.info("Invalidated basket snapshots for slug=%s, deleted %d keys", slug, deleted)


def invalidate_all_product_cache():
    """
    Invalidate **all** product‑related caches (detail pages, lists,
    filters, attributes, counts).
    """
    prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
    if prefix:
        pattern = f"{prefix}:*products*"
    else:
        pattern = "products:*"
    deleted = delete_keys_by_pattern(pattern)
    logger.info("All product caches invalidated, deleted %d keys", deleted)
