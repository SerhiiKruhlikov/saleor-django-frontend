# compare/views.py
from django.http import JsonResponse, Http404
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import activate, deactivate_all
from .services import get_product_snapshot


def compare_product_api(request, slug):
    """
    API endpoint that returns a product snapshot for comparison.
    """
    lang = request.GET.get("lang", settings.LANGUAGE_CODE)
    snapshot = get_product_snapshot(slug, language=lang)
    if snapshot is None:
        raise Http404("Product not found")
    return JsonResponse(snapshot)


def compare_page(request):
    """Render the compare page shell. The table will be loaded via HTMX."""
    return render(request, "compare/compare.html")


def compare_table_api(request):
    """
    HTMX endpoint that returns an HTML fragment containing the comparison table.

    Expects a comma‑separated list of product slugs in the ``slugs`` GET
    parameter.  Each slug is resolved via :func:`~compare.services.get_product_snapshot`,
    and the resulting snapshots are rendered into the
    ``compare/compare_table.html`` template.
    """
    slugs_str = request.GET.get("slugs", "")
    if not slugs_str:
        return HttpResponse("<p>No products to compare.</p>")

    slugs = [s.strip() for s in slugs_str.split(",") if s.strip()]
    lang = request.GET.get("lang", request.LANGUAGE_CODE)

    activate(lang)                       # активируем запрошенный язык
    try:
        snapshots = []
        for slug in slugs:
            snap = get_product_snapshot(slug, language=lang)
            if snap is not None:
                snapshots.append(snap)

        if not snapshots:
            return HttpResponse("<p>Could not load any products for comparison.</p>")

        context = {"snapshots": snapshots}
        return render(request, "compare/compare_table.html", context)
    finally:
        deactivate_all()
