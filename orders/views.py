# orders/views.py
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .services import get_order


def order_detail(request, order_id):
    order = get_order(order_id)
    if order is None:
        raise Http404("Order not found")

    context = {
        "order": order,
    }
    return render(request, "orders/order_detail.html", context)
