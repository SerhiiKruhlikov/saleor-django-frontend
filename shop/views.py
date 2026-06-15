# home/views.py
from django.shortcuts import render


def index(request, context=None):
    return render(request, "shop/index.html", context)


def custom_404(request, exception):
    """
    Render a friendly 404 page depending on the URL prefix.
    """
    if request.path.startswith("/catalog/"):
        template = "categories/404.html"
        context = {"message": "Категорію не знайдено"}
    elif request.path.startswith("/product/"):
        template = "products/404.html"
        context = {"message": "Товар не знайдено"}
    else:
        template = "404.html"
        context = {"message": "Сторінку не знайдено"}

    return render(request, template, context, status=404)
