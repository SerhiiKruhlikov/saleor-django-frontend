# categories/services/categories.py
from gateway.saleor.loader import load_query
from gateway.saleor.client import execute_query
from django.core.cache import cache

APP_NAME = "categories"


def get_category_count() -> int:
    """
    Returns the total number of categories (cached in Redis).

    The value is fetched from Saleor once every 10 minutes, or until the
    cache is explicitly invalidated.

    Returns:
        Total number of categories (int).

    Raises:
        requests.HTTPError: If there is a connection error or an invalid
            response from Saleor.
    """
    return cache.get_or_set(
        "category_total_count",
        _fetch_category_count,
        timeout=600,
    )


def _fetch_category_count() -> int:
    """Executes the GraphQL query to obtain the number of categories."""
    query = load_query(APP_NAME, "queries/category_count.graphql")
    data = execute_query(query)
    return data["categories"]["totalCount"]


def get_all_categories(first: int | None = None) -> list[dict]:
    """
    Retrieves a flat list of all categories from Saleor (cached).

    When ``first`` is ``None``, the total count is obtained automatically
    (also cached) and all categories are loaded. The result is stored in
    Redis with a key that includes the ``first`` parameter.

    Args:
        first: Maximum number of categories (``None`` to fetch all).

    Returns:
        List of dictionaries, each containing ``id``, ``name``, ``slug``,
        and ``parent`` (``None`` or a dict with ``id``).

    Example:
        >>> cats = get_all_categories(first=10)
        >>> cats[0]["name"]
        'Catalog'
    """
    if first is None:
        first = get_category_count()

    cache_key = f"all_categories_first_{first}"
    categories = cache.get(cache_key)
    if categories is None:
        query = load_query(APP_NAME, "queries/all_categories.graphql")
        variables = {"first": first}
        data = execute_query(query, variables)
        categories = [edge["node"] for edge in data["categories"]["edges"]]
        cache.set(cache_key, categories, timeout=600)
    return categories


def get_category_by_slug(slug: str) -> dict:
    """
    Retrieves a single category by its slug (cached for 30 minutes).

    Executes the ``category_by_slug.graphql`` query, passing the ``slug``
    variable. The result is stored in Redis under a slug‑specific key.

    Args:
        slug: URL identifier of the category (e.g. ``"video-walls"``).

    Returns:
        Category dictionary, or ``None`` if the category is not found.
        ``None`` values are **not** cached.

    Raises:
        requests.HTTPError: If there is a problem with the request.
    """
    cache_key = f"category_slug_{slug}"
    category = cache.get(cache_key)
    if category is None:
        query = load_query(APP_NAME, "queries/category_by_slug.graphql")
        variables = {"slug": slug}
        data = execute_query(query, variables)
        category = data.get("category")
        if category is not None:
            cache.set(cache_key, category, timeout=1800)
    return category


def get_full_tree() -> list[dict]:
    """
    Returns the full category tree (cached in Redis for 1 hour).

    Loads all categories via :func:`get_all_categories` without a limit,
    builds the tree using :func:`build_category_tree`, and stores the
    result until it expires or is invalidated.

    Returns:
        Category tree (list of root nodes with nested ``children``).
    """
    return cache.get_or_set(
        "full_category_tree",
        _compute_full_tree,
        timeout=3600,
    )


def _compute_full_tree() -> list[dict]:
    """Builds the complete category tree without caching."""
    flat = get_all_categories()
    return build_category_tree(flat)


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

def invalidate_category_cache():
    """
    Invalidates all cached data related to categories.

    Removes specific keys as well as wildcard patterns, so that the next
    request to any of the cached functions will fetch fresh data from Saleor.
    Pattern deletion requires the Redis cache backend.
    """
    cache.delete("category_total_count")
    cache.delete("full_category_tree")
    cache.delete_pattern("all_categories_*")
    cache.delete_pattern("category_slug_*")
