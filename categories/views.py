# categories/views.py
from django.http import Http404
from django.shortcuts import render

from categories.services.categories import get_full_tree, get_category_by_slug, find_node_in_tree
from shop.services.breadcrumbs import get_breadcrumbs_for_category


def index(request, slug):
    breadcrumbs = get_breadcrumbs_for_category(slug)
    category = get_category_by_slug(slug)
    if not category:
        raise Http404("Категорію не знайдено")

    full_tree = get_full_tree()
    subcategories = find_node_in_tree(slug, full_tree)

    context = {
        "breadcrumbs": breadcrumbs,
        "category": category,
        "subcategories": subcategories,
    }

    return render(request, "categories/index.html", context)


def detail(request, slug):
    breadcrumbs = get_breadcrumbs_for_category(slug)
    category = get_category_by_slug(slug)
    if not category:
        raise Http404("Категорію не знайдено")

    full_tree = get_full_tree()
    subcategories = find_node_in_tree(slug, full_tree)

    context = {
        "breadcrumbs": breadcrumbs,
        "category": category,
        "subcategories": subcategories,
        "parent": category.get("parent"),
    }

    return render(request, "categories/detail.html", context)
