# categories/views.py
from django.utils.translation import gettext as _

from django.shortcuts import render
from django.http import Http404

from gateway.saleor.client import SaleorUnavailable
from shop.services.breadcrumbs import get_breadcrumbs_for_category
from categories.services.categories import (
    get_full_tree,
    get_category_by_slug,
    find_node_in_tree,
)


def index(request, slug='catalog'):
    """
    Root catalog page – shows the top-level category "catalog".

    If the category data cannot be loaded, an error flag is passed
    to the template and the page still renders without breaking.
    """
    context = {
        "category": None,
        "subcategories": None,
        "breadcrumbs": [],
        "category_error": False,
        "parent": None,
    }

    category = get_category_by_slug(slug, language=request.LANGUAGE_CODE)
    if category is None:
        context["category_error"] = True
        return render(request, "categories/index.html", context)

    context["category"] = category
    context["parent"] = category.get("parent")

    full_tree = get_full_tree(language=request.LANGUAGE_CODE)
    if full_tree:
        subcategories = find_node_in_tree(slug, full_tree)
        context["subcategories"] = subcategories
    else:
        context["subcategories"] = None

    try:
        context["breadcrumbs"] = get_breadcrumbs_for_category(slug)
    except Exception:
        context["breadcrumbs"] = []

    return render(request, "categories/index.html", context)


def detail(request, slug):
    """
    Detail page for a specific category.

    If Saleor is unavailable, a friendly error page is shown.
    If the category does not exist, a 404 is raised.
    """
    try:
        category = get_category_by_slug(slug, language=request.LANGUAGE_CODE)
    except SaleorUnavailable:
        return render(request, "categories/detail.html", {
            "category": None,
            "tree_error": True,
            "subcategories": None,
            "breadcrumbs": [],
            "parent": None,
        })

    if category is None:
        raise Http404(_("Category not found"))

    context = {
        "category": category,
        "subcategories": None,
        "breadcrumbs": [],
        "tree_error": False,
        "parent": category.get("parent"),
    }

    full_tree = get_full_tree(language=request.LANGUAGE_CODE)
    if full_tree:
        subcategories = find_node_in_tree(slug, full_tree)
        context["subcategories"] = subcategories
    else:
        context["tree_error"] = True

    try:
        context["breadcrumbs"] = get_breadcrumbs_for_category(slug)
    except Exception:
        context["breadcrumbs"] = []

    # Parse filter params from the URL if present (e.g. /filter/status-.../)
    filter_query_string = ''
    if '/filter/' in request.path_info:
        from router.services import parse_filter_url
        filter_params = parse_filter_url(request.path_info)
        if filter_params:
            # Build a query string to pass to HTMX
            filter_query_string = '&'.join(
                f'attr_{k}={v}' for k, values in filter_params.items() for v in values
            )
    context['filter_query_string'] = filter_query_string

    # Определяем, есть ли товары в категории, чтобы показывать панель фильтров
    # Запрашиваем только количество товаров без загрузки всех
    from products.services.products import get_category_product_count
    product_count = get_category_product_count(slug, language=request.LANGUAGE_CODE)
    context['show_filters'] = product_count > 0

    return render(request, "categories/detail.html", context)
