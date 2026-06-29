# products/views.py
from django.utils.translation import gettext as _
from django.utils.translation import activate, deactivate_all

from django.conf import settings
from django.shortcuts import render
from django.http import Http404

from gateway.saleor.client import SaleorUnavailable
from products.services.products import (
    get_product_by_slug,
    get_category_with_filters,
)
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
        return render(
            request,
            "products/detail.html",
            {
                "product": None,
                "product_error": True,
                "breadcrumbs": [],
                "parent": None,
            },
        )

    if product is None:
        raise Http404(_("Product not found"))

    breadcrumbs = get_breadcrumbs_for_product(product, request.LANGUAGE_CODE)

    context = {
        "product": product,
        "breadcrumbs": breadcrumbs,
        "parent": product.get("category"),
        "product_error": False,
    }
    return render(request, "products/detail.html", context)


def products_fragment(request, slug):
    """
    Return HTML fragment with only products (for "Show more" pagination).
    """
    first = settings.SALEOR_PAGINATION_PRODUCTS_PER_PAGE
    after = request.GET.get("after")
    lang = request.GET.get("lang", request.LANGUAGE_CODE)

    # Parse selected filters from query string (supports multiple values per attribute)
    selected_filters = {}
    for key in request.GET:
        if key.startswith("attr_"):
            attr_slug = key[5:]
            selected_filters[attr_slug] = request.GET.getlist(key)

    activate(lang)
    try:
        # Always use the unified method that returns products with attributes and status
        data = get_category_with_filters(
            slug,
            selected_filters=selected_filters if selected_filters else None,
            first=first,
            after=after,
            language=lang,
        )
        products_data = data["products"]

        context = {
            "products": products_data["edges"],
            "page_info": products_data["page_info"],
            "category_slug": slug,
            "selected_filters": selected_filters,
            "request": request,
        }

        loaded_raw = request.GET.get('loaded', len(products_data['edges']))
        try:
            loaded = int(loaded_raw)
        except (ValueError, TypeError):
            loaded = len(products_data['edges'])

        total_count_raw = products_data.get('total_count', 0)
        total_count = int(total_count_raw)
        next_page_count = min(first, total_count - loaded) if total_count > loaded else 0
        remaining_total = total_count - loaded
        new_loaded = loaded + next_page_count

        context.update({
            'loaded': loaded,
            'next_page_count': next_page_count,
            'remaining_total': remaining_total,
            'new_loaded': new_loaded,
        })

        return render(request, "products/product_list_fragment.html", context)
    finally:
        deactivate_all()


def category_fragment(request, slug):
    """
    Return HTML fragments for filters, selected tags, and initial products
    as OOB swaps for HTMX.

    The response includes an ``HX-Push-Url`` header so the browser URL
    is updated to a user‑friendly form (e.g. /.../filter/status-value/).
    """
    lang = request.GET.get("lang", request.LANGUAGE_CODE)
    first = settings.SALEOR_PAGINATION_PRODUCTS_PER_PAGE

    # Parse selected filters – use getlist to support multiple values per attribute
    selected_filters = {}
    for key in request.GET:
        if key.startswith("attr_"):
            attr_slug = key[5:]
            selected_filters[attr_slug] = request.GET.getlist(key)

    activate(lang)
    try:
        data = get_category_with_filters(
            slug,
            selected_filters=selected_filters if selected_filters else None,
            first=first,
            after=None,
            language=lang,
        )

        # Build display-friendly structure for selected filters
        selected_filters_display = []
        if data['filters'] is not None:               # avoid None for empty categories
            for attr in data['filters']:
                attr_slug = attr['slug']
                selected_vals = selected_filters.get(attr_slug, [])
                if not selected_vals:
                    continue
                values_display = []
                for val in attr['values']:
                    if val['slug'] in selected_vals:
                        values_display.append({
                            'slug': val['slug'],
                            'name': val.get('name', val['slug']),
                        })
                selected_filters_display.append({
                    'slug': attr_slug,
                    'name': attr['name'],
                    'values': values_display,
                })

        context = {
            "filters": data["filters"],
            "products": data["products"]["edges"],
            "page_info": data["products"]["page_info"],
            "total_count": data["products"]["total_count"],
            "category_slug": slug,
            "selected_filters": selected_filters,
            'selected_filters_display': selected_filters_display,
            "request": request,
        }

        # loaded: how many products are already shown to the user
        loaded_raw = request.GET.get('loaded', len(data['products']['edges']))

        try:
            loaded = int(loaded_raw)
        except (ValueError, TypeError):
            loaded = 0

        total_count_raw = data['products']['total_count']
        total_count = int(total_count_raw)
        next_page_count = min(first, total_count - loaded) if total_count > loaded else 0
        remaining_total = total_count - loaded
        new_loaded = loaded + next_page_count

        context.update({
            'loaded': loaded,
            'next_page_count': next_page_count,
            'remaining_total': remaining_total,
            'new_loaded': new_loaded,
        })

        response = render(request, "products/category_fragment.html", context)

        # Build a pretty browser URL in filter style (no /api/ prefix, no lang param
        # for default language)
        from django.urls import reverse
        pretty_url = reverse("router:dynamic_router", kwargs={"slug": slug})
        filter_parts = []
        for attr_slug, values in selected_filters.items():
            value_str = "-or-".join(values)
            filter_parts.append(f"{attr_slug}-{value_str}")
        if filter_parts:
            pretty_url += "filter/" + "/".join(filter_parts) + "/"
        response["HX-Push-Url"] = pretty_url
        return response
    finally:
        deactivate_all()
