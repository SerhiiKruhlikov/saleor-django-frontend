# products/services/products.py
import json
import logging

from django.conf import settings
from django.core.cache import cache

from gateway.saleor.client import safe_execute_query, SaleorUnavailable
from gateway.saleor.loader import load_query

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
                return {
                    "edges": pdata.get("edges", []),
                    "page_info": pdata.get("pageInfo", {}),
                    "total_count": pdata.get("totalCount", 0),
                }
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
                attr_names[attr_slug] = attr["attribute"]["name"]
                for value in attr["values"]:
                    val_slug = value["slug"]
                    attr_counts[attr_slug][val_slug] += 1
                    value_names[attr_slug][val_slug] = value.get("name", val_slug)

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
