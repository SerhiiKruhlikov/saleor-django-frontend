# home/views.py
from django.shortcuts import render


def index(request, context=None):
    return render(request, "shop/index.html", context)
