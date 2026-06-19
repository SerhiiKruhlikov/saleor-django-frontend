# products/api_urls.py
from django.urls import path
from products.views import products_fragment, category_fragment

urlpatterns = [
    path('<slug:slug>/', products_fragment, name='products_fragment'),
    path('category/<slug:slug>/', category_fragment, name='category_fragment'),
]
