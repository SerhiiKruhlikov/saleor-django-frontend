# basket/views.py
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render
from django.utils.translation import activate, deactivate_all
from django.conf import settings

from basket.services import create_order
from products.services.products import get_product_snapshot


@require_POST
@csrf_exempt
def checkout_create(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = data.get("email")
    if not email:
        return JsonResponse({"error": "Email is required"}, status=400)

    address_data = {
        "firstName": data.get("firstName"),
        "lastName": data.get("lastName"),
        "phone": data.get("phone"),
        "city": data.get("city"),
        "streetAddress1": data.get("streetAddress1"),
        "postalCode": data.get("postalCode", ""),
        "country": data.get("country", "UA"),
    }

    items_data = data.get("items", [])
    if not items_data:
        return JsonResponse({"error": "No products in basket"}, status=400)

    items = []
    for item_data in items_data:
        slug = item_data.get("slug")
        quantity = item_data.get("quantity", 1)
        snap = get_product_snapshot(slug, language=request.LANGUAGE_CODE)
        if not snap:
            return JsonResponse({"error": f"Product {slug} not found"}, status=400)
        variant_id = snap.get("variant_id")
        if not variant_id:
            return JsonResponse({"error": f"Product {slug} has no variant"}, status=400)
        items.append({"variant_id": variant_id, "quantity": quantity})

    result = create_order(email, address_data, items)
    if result["success"]:
        return JsonResponse({"status": "ok", "order_id": result["order_id"]})
    else:
        return JsonResponse({"status": "error", "message": result["error"]}, status=400)


def checkout_page(request):
    return render(request, 'basket/checkout.html')


def checkout_table_api(request):
    items_str = request.GET.get('items', '')

    try:
        items_data = json.loads(items_str) if items_str else []
    except json.JSONDecodeError:
        items_data = []

    if not items_data:
        return HttpResponse("<p>{% trans 'No products in basket.' %}</p>")

    lang = request.GET.get('lang', request.LANGUAGE_CODE)
    activate(lang)

    try:
        quantities = {item['slug']: item['quantity'] for item in items_data}

        items = []
        for slug, quantity in quantities.items():
            snap = get_product_snapshot(slug, language=lang)
            if snap:
                snap['quantity'] = quantity
                items.append(snap)

        subtotal = sum(
            item.get('price', {}).get('amount', 0) * item.get('quantity', 1)
            for item in items
        )

        context = {
            'items': items,
            'subtotal': subtotal,
        }
        response = render(request, 'basket/checkout_table.html', context)
        return response
    finally:
        deactivate_all()


def basket_page(request):
    """
    Basket page shell. The content will be loaded via HTMX.
    """
    return render(request, "basket/basket.html")


def basket_snapshots_api(request):
    """
    Return JSON with product snapshots for the given slugs.
    GET parameters:
        slugs – comma-separated list of product slugs
        lang  – language code (default: request.LANGUAGE_CODE)
    """
    slugs_str = request.GET.get("slugs", "")
    if not slugs_str:
        return JsonResponse({"snapshots": []})

    slugs = [s.strip() for s in slugs_str.split(",") if s.strip()]
    lang = request.GET.get("lang", request.LANGUAGE_CODE)

    snapshots = []
    for slug in slugs:
        snap = get_product_snapshot(slug, language=lang)
        if snap is not None:
            snapshots.append(snap)

    return JsonResponse({"snapshots": snapshots})


def basket_table_api(request):
    items_str = request.GET.get('items', '')
    if items_str:
        try:
            items_data = json.loads(items_str)
        except json.JSONDecodeError:
            items_data = []
    else:
        slugs_str = request.GET.get('slugs', '')
        slugs = [s.strip() for s in slugs_str.split(',') if s.strip()]
        items_data = [{'slug': slug, 'quantity': 1} for slug in slugs]

    if not items_data:
        return HttpResponse("<p>{% trans 'No products in basket.' %}</p>")

    lang = request.GET.get('lang', request.LANGUAGE_CODE)
    activate(lang)

    try:
        quantities = {item['slug']: item['quantity'] for item in items_data}

        items = []
        unavailable = []
        for item_data in items_data:
            slug = item_data['slug']
            snap = get_product_snapshot(slug, language=lang)
            if snap is None:
                unavailable.append({"slug": slug, "name": slug, "price": "—"})
            elif not snap.get("available_for_purchase"):
                unavailable.append(snap)
            else:
                snap['quantity'] = quantities.get(slug, 1)
                items.append(snap)

        subtotal = sum(
            item.get('price', {}).get('amount', 0) * item.get('quantity', 1)
            for item in items
        )

        context = {
            'items': items,
            'unavailable': unavailable,
            'subtotal': subtotal,
        }
        response = render(request, 'basket/basket_table.html', context)
        return response
    finally:
        deactivate_all()
