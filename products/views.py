from django.http import Http404
from django.shortcuts import render

from products.services.products import get_product_by_slug


def detail(request, slug):

    product = get_product_by_slug(slug)
    if not product:
        raise Http404("Товар не знайдено")

    context = {
        "product": product,
        "parent": product["category"],
    }

    return render(request, "products/detail.html", context)
