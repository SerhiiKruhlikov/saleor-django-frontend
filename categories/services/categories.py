# categories/services/categories.py
from django.conf import settings
from gateway.saleor.loader import load_query
from gateway.saleor.client import safe_execute_query, SaleorUnavailable
from django.core.cache import cache

APP_NAME = "categories"

# ----------------------------------------------------------------------
# Cache timeouts from settings (with sensible defaults)
# ----------------------------------------------------------------------
CACHE_TIMEOUTS = getattr(settings, 'CACHE_TIMEOUTS', {})

TIMEOUT_CATEGORY_COUNT = CACHE_TIMEOUTS.get('CATEGORY_COUNT', 600)
TIMEOUT_ALL_CATEGORIES = CACHE_TIMEOUTS.get('ALL_CATEGORIES', 600)
TIMEOUT_CATEGORY_BY_SLUG = CACHE_TIMEOUTS.get('CATEGORY_BY_SLUG', 1800)
TIMEOUT_FULL_TREE = CACHE_TIMEOUTS.get('FULL_TREE', 3600)

# Short TTL for caching "not found" results (e.g., non-existent slugs)
TIMEOUT_NONE = 60


def get_category_count() -> int:
    """
    Returns the total number of categories (cached in Redis).

    If Saleor is unreachable, returns 0 so the page can still render.
    The error is logged by the client layer.
    """
    return cache.get_or_set(
        "category_total_count",
        _fetch_category_count_safe,
        timeout=TIMEOUT_CATEGORY_COUNT,
    )


def _fetch_category_count_safe() -> int:
    """Fetch the category count, returning 0 on any error."""
    try:
        query = load_query(APP_NAME, "queries/category_count.graphql")
        data = safe_execute_query(query)
        if data is None:
            return 0
        return data.get("categories", {}).get("totalCount", 0)
    except SaleorUnavailable:
        return 0


def get_all_categories(first: int | None = None) -> list[dict]:
    """
    Retrieves a flat list of all categories from Saleor (cached).

    When ``first`` is ``None``, the total count is obtained automatically
    (also cached) and all categories are loaded.  On failure an empty
    list is returned, and the error is logged.

    Args:
        first: Maximum number of categories (``None`` to fetch all).

    Returns:
        List of dictionaries, each containing ``id``, ``name``, ``slug``,
        and ``parent`` (``None`` or a dict with ``id``).  Empty list on error.

    Example:
        >>> cats = get_all_categories(first=10)
        >>> cats[0]["name"]
        'Catalog'
    """
    if first is None:
        first = get_category_count()
        if first == 0:
            return []

    cache_key = f"all_categories_first_{first}"
    categories = cache.get(cache_key)
    if categories is None:
        try:
            query = load_query(APP_NAME, "queries/all_categories.graphql")
            variables = {"first": first}
            data = safe_execute_query(query, variables)
            if data is None:
                return []
            categories = [
                edge["node"] for edge in data.get("categories", {}).get("edges", [])
            ]
            if categories:
                cache.set(cache_key, categories, timeout=TIMEOUT_ALL_CATEGORIES)
        except SaleorUnavailable:
            return []
    return categories or []


def get_category_by_slug(slug: str) -> dict | None:
    """
    Retrieves a single category by its slug (cached).

    If Saleor returns ``null`` for the slug, ``None`` is returned and
    **cached with a short TTL** to avoid repeated queries.
    If Saleor is unreachable, ``None`` is returned **without caching**,
    so the next request can retry.

    Args:
        slug: URL identifier of the category (e.g. ``"video-walls"``).

    Returns:
        Category dictionary, or ``None`` if the category is not found
        or an error occurs.
    """
    cache_key = f"category_slug_{slug}"
    category = cache.get(cache_key)
    if category is None:
        try:
            query = load_query(APP_NAME, "queries/category_by_slug.graphql")
            variables = {"slug": slug}
            data = safe_execute_query(query, variables)
            if data is None:
                # Entity not found – cache the None result briefly
                cache.set(cache_key, None, timeout=TIMEOUT_NONE)
                return None
            category = data.get("category")
            if category is not None:
                cache.set(cache_key, category, timeout=TIMEOUT_CATEGORY_BY_SLUG)
            else:
                cache.set(cache_key, None, timeout=TIMEOUT_NONE)
        except SaleorUnavailable:
            # Do not cache on error – allow a retry on the next request
            return None
    return category


def get_full_tree() -> list[dict]:
    """
    Returns the full category tree (cached in Redis for 1 hour).

    If Saleor cannot be reached, returns an empty list so the menu
    can degrade gracefully.  The error is logged by the client layer.

    Returns:
        Category tree (list of root nodes with nested ``children``),
        or an empty list on failure.
    """
    return cache.get_or_set(
        "full_category_tree",
        _compute_full_tree_safe,
        timeout=TIMEOUT_FULL_TREE,
    ) or []


def _compute_full_tree_safe() -> list[dict]:
    """Builds the complete category tree, returning [] on error."""
    try:
        flat = get_all_categories()
        if not flat:
            return []
        return build_category_tree(flat)
    except SaleorUnavailable:
        return []


def build_category_tree(categories: list[dict]) -> list[dict]:
    """
    Converts a flat list of categories into a tree (children in ``children`` key).

    Each category receives an additional ``children`` key (list).
    Categories with ``parent=None`` become root nodes, the rest
    are distributed to their parents according to ``parent.id``.

    Args:
        categories: Flat list of dictionaries, each of which must
            contain ``id`` and ``parent`` (``None`` or dict with ``id`` key).

    Returns:
        List of root categories with recursively nested subcategories
        in the ``children`` field.

    Example:
        >>> flat = [
        ...   {"id": "1", "name": "A", "parent": None},
        ...   {"id": "2", "name": "B", "parent": {"id": "1"}},
        ... ]
        >>> tree = build_category_tree(flat)
        >>> tree[0]["children"][0]["name"]
        'B'
    """
    for cat in categories:
        cat.setdefault("children", [])
        cat.setdefault("parent_node", None)
    lookup = {cat["id"]: cat for cat in categories}
    roots = []
    for cat in categories:
        parent = cat.get("parent")
        if parent is None:
            roots.append(cat)
        else:
            parent_id = parent["id"] if isinstance(parent, dict) else parent
            lookup[parent_id]["children"].append(cat)
            cat["parent_node"] = lookup[parent_id]
    return roots


def find_node_in_tree(slug: str, nodes: list[dict]) -> dict | None:
    """
    Recursively searches for a node with the given slug in the category tree.

    Used to highlight the active menu branch or build a subtree
    on the category detail page.

    Args:
        slug: URL identifier of the category to find.
        nodes: List of tree nodes (usually the result of :func:`get_full_tree`
            or the ``children`` of some node).

    Returns:
        Node dictionary (with ``children`` field) or ``None`` if the node
        is not found.

    Example:
        >>> full_tree = get_full_tree()
        >>> node = find_node_in_tree("video-walls", full_tree)
        >>> node["name"]
        'Video Walls'
    """
    for node in nodes:
        if node.get("slug") == slug:
            return node
        found = find_node_in_tree(slug, node.get("children", []))
        if found:
            return found
    return None


# ----------------------------------------------------------------------
# Cache invalidation
# ----------------------------------------------------------------------

def invalidate_global_category_cache():
    """
    Invalidates shared category cache keys: total count, full tree,
    and all flat lists.

    Does **not** remove individual ``category_slug_*`` keys.
    """
    cache.delete("category_total_count")
    cache.delete("full_category_tree")
    cache.delete_pattern("all_categories_*")
