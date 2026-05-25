# shop/services/breadcrumbs.py
from categories.services.categories import get_full_tree, find_node_in_tree


def _build_category_chain(category_slug: str) -> list[dict]:
    """
    Build a chain of categories from the given slug up to the root.

    Each element in the returned list is a dictionary with ``name`` and
    ``url``.  All elements are clickable (``url`` is not ``None``).

    Args:
        category_slug: URL identifier of the category to start from.

    Returns:
        List of category dictionaries ordered from the highest ancestor
        (root) down to the requested category (inclusive).  Returns an
        empty list when the slug cannot be found in the tree.
    """
    full_tree = get_full_tree()
    node = find_node_in_tree(category_slug, full_tree)
    if not node:
        return []

    chain = []
    current = node
    while current is not None:
        if current.get("parent_node") is None:
            url = "/catalog/"
        else:
            url = f"/catalog/{current['slug']}/"
        chain.append({"name": current["name"], "url": url})
        current = current.get("parent_node")
    chain.reverse()
    return chain


def get_breadcrumbs_for_category(category_slug: str) -> list[dict]:
    """
    Return breadcrumb items for a category page.

    The last item in the list is the current category and is **not**
    clickable (``url`` is ``None``).

    Args:
        category_slug: URL identifier of the category.

    Returns:
        List of breadcrumb items, each with ``name`` and ``url``.
    """
    chain = _build_category_chain(category_slug)
    if chain:
        chain[-1]["url"] = None
    return chain


def get_breadcrumbs_for_product(product: dict) -> list[dict]:
    """
    Return breadcrumb items for a product detail page.

    Builds the category chain using the product's category slug and
    appends the product itself as the last, non-clickable element.

    Args:
        product: Dictionary that must contain a ``category`` key with a
            ``slug`` sub‑key, and a ``name`` key for the product name.

    Returns:
        List of breadcrumb items.  All category items are clickable;
        the final product item has ``url`` set to ``None``.
    """
    category_slug = product.get("category", {}).get("slug")
    if not category_slug:
        return []

    chain = _build_category_chain(category_slug)
    chain.append({"name": product["name"], "url": None})
    return chain
