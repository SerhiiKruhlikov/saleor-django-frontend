# products/views.py
from django.utils.translation import gettext as _
from django.utils.translation import activate, deactivate_all

from django.conf import settings
from django.shortcuts import render
from django.http import Http404

from gateway.saleor.client import SaleorUnavailable
from products.services.products import get_product_by_slug, get_products_by_category
from shop.services.breadcrumbs import get_breadcrumbs_for_product


def detail(request, slug):
    """
    Product detail page.

    If Saleor is unavailable, a friendly error message is shown.
    If the product does not exist, a 404 is raised (which will use
    the custom ``products/404.html`` template).
    """
    try:
        product = get_product_by_slug(slug, language=request.LANGUAGE_CODE)
    except SaleorUnavailable:
        return render(request, "products/detail.html", {
            "product": None,
            "product_error": True,
            "breadcrumbs": [],
            "parent": None,
        })

    if product is None:
        raise Http404(_("Product not found"))

    breadcrumbs = get_breadcrumbs_for_product(product)

    context = {
        "product": product,
        "breadcrumbs": breadcrumbs,
        "parent": product.get("category"),
        "product_error": False,
    }
    return render(request, "products/detail.html", context)


def products_fragment(request, slug):
    """Return HTML fragment with products and pagination for HTMX."""
    first = settings.SALEOR_PAGINATION_PRODUCTS_PER_PAGE
    after = request.GET.get('after')
    lang = request.GET.get('lang', request.LANGUAGE_CODE)

    activate(lang)
    try:
        data = get_products_by_category(slug, first=first, after=after, language=lang)

        context = {
            'products': data['edges'],
            'page_info': data['page_info'],
            'category_slug': slug,
        }
        return render(request, 'products/product_list_fragment.html', context)
    finally:
        deactivate_all()
