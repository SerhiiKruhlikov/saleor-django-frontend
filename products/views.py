from django.http import Http404
from django.shortcuts import render

from products.services.products import get_product_by_slug
from shop.services.breadcrumbs import get_breadcrumbs_for_product


def detail(request, slug):

    product = get_product_by_slug(slug)
    if not product:
        raise Http404("Товар не знайдено")

    breadcrumbs = get_breadcrumbs_for_product(product)

    context = {
        "breadcrumbs": breadcrumbs,
        "product": product,
        "parent": product["category"],
    }

    return render(request, "products/detail.html", context)
