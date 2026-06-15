# products/views.py
from django.shortcuts import render
from django.http import Http404

from gateway.saleor.client import SaleorUnavailable
from products.services.products import get_product_by_slug
from shop.services.breadcrumbs import get_breadcrumbs_for_product


def detail(request, slug):
    """
    Product detail page.

    If Saleor is unavailable, a friendly error message is shown.
    If the product does not exist, a 404 is raised (which will use
    the custom ``products/404.html`` template).
    """
    try:
        product = get_product_by_slug(slug)
    except SaleorUnavailable:
        return render(request, "products/detail.html", {
            "product": None,
            "product_error": True,
            "breadcrumbs": [],
            "parent": None,
        })

    if product is None:
        raise Http404("Товар не знайдено")

    breadcrumbs = get_breadcrumbs_for_product(product)

    context = {
        "product": product,
        "breadcrumbs": breadcrumbs,
        "parent": product.get("category"),
        "product_error": False,
    }
    return render(request, "products/detail.html", context)
