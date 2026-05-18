# categories/services/categories.py
from gateway.saleor.loader import load_query
from gateway.saleor.client import execute_query
from functools import lru_cache

APP_NAME = "categories"


@lru_cache(maxsize=1)
def _cached_category_count() -> int:
    """
    Returns the cached total number of categories.

    A wrapper function that queries the number of categories
    from Saleor once and stores the result until the process restarts.
    Used inside :func:`get_all_categories` when called without the `first` argument.

    Returns:
        Total number of categories in the store.
    """
    return get_category_count()


def get_category_count() -> int:
    """
    Queries the total number of categories from Saleor.

    Executes the GraphQL query ``category_count.graphql`` and returns the number
    that can be used to limit the results in :func:`get_all_categories`.

    Returns:
        Total number of categories (int).

    Raises:
        requests.HTTPError: If there is a connection error or an invalid response from Saleor.
    """
    query = load_query(APP_NAME, "queries/category_count.graphql")
    data = execute_query(query)
    return data["categories"]["totalCount"]


def get_all_categories(first: int | None = None) -> list[dict]:
    """
    Retrieves a flat list of all categories from Saleor.

    If the ``first`` parameter is not provided, it automatically queries
    the total number of categories via :func:`_cached_category_count`
    and loads all of them. The result is extracted from the
    ``edges → node`` structure and returned as a list of dictionaries.

    Args:
        first: Maximum number of categories (None – all).

    Returns:
        List of dictionaries, where each item contains:
        ``id``, ``name``, ``slug``, ``parent`` (None or dict with ``id``).

    Example:
        >>> cats = get_all_categories(first=10)
        >>> cats[0]['name']
        'Catalog'
    """
    if first is None:
        first = _cached_category_count()
    query = load_query(APP_NAME, "queries/all_categories.graphql")
    variables = {"first": first}
    data = execute_query(query, variables)
    return [edge["node"] for edge in data["categories"]["edges"]]


def get_category_by_slug(slug: str) -> dict:
    """
    Retrieves a single category by its slug (human-readable URL).

    Executes the query ``category_by_slug.graphql``, passing the ``slug`` variable.
    Returns a dictionary with the full set of category fields, including parent,
    children, and description.

    Args:
        slug: URL identifier of the category (e.g., ``"video-walls"``).

    Returns:
        Category dictionary or ``None`` if the category is not found.

    Raises:
        requests.HTTPError: If there is a problem with the request.
    """
    query = load_query(APP_NAME, "queries/category_by_slug.graphql")
    variables = {"slug": slug}
    data = execute_query(query, variables)
    return data["category"]


def build_category_tree(categories: list[dict]) -> list[dict]:
    """
    Converts a flat list of categories into a tree (children in the ``children`` key).

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
    lookup = {cat["id"]: cat for cat in categories}
    roots = []
    for cat in categories:
        parent = cat.get("parent")
        if parent is None:
            roots.append(cat)
        else:
            parent_id = parent["id"] if isinstance(parent, dict) else parent
            lookup[parent_id]["children"].append(cat)
    return roots


def get_full_tree() -> list[dict]:
    """
    Returns the full category tree (cached).

    Loads all categories via :func:`get_all_categories` without a limit,
    then builds the tree using :func:`build_category_tree`.
    The result can be cached globally for better performance.

    Returns:
        Category tree (list of root nodes with nested ``children``).

    Note:
        For production, it is recommended to add caching at the Django level
        (e.g., ``django.core.cache``) so that all categories are not
        queried on every call.
    """
    flat = get_all_categories()
    return build_category_tree(flat)


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
        Node dictionary (with ``children`` field) or ``None`` if the node is not found.

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
