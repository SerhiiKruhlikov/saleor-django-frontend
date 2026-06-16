# shop/services/breadcrumbs.py
from categories.services.categories import get_full_tree, find_node_in_tree


def _build_category_chain(category_slug: str) -> list[dict]:
    """Builds a chain of categories from the given slug up to the root."""
    full_tree = get_full_tree()
    node = find_node_in_tree(category_slug, full_tree)
    if not node:
        return []

    chain = []
    current = node
    while current is not None:
        if current.get("parent_node") is None:
            # Корень каталога – генерируем URL через роутер
            from django.urls import reverse
            url = reverse('router:dynamic_router', kwargs={'slug': 'catalog'})
        else:
            from django.urls import reverse
            url = reverse('router:dynamic_router', kwargs={'slug': current['slug']})
        chain.append({"name": current["name"], "url": url})
        current = current.get("parent_node")
    chain.reverse()
    return chain


def get_breadcrumbs_for_category(category_slug: str) -> list[dict]:
    chain = _build_category_chain(category_slug)
    if chain:
        chain[-1]["url"] = None
    return chain


def get_breadcrumbs_for_product(product: dict) -> list[dict]:
    category_slug = product.get("category", {}).get("slug")
    if not category_slug:
        return []

    chain = _build_category_chain(category_slug)
    chain.append({"name": product["name"], "url": None})
    return chain
