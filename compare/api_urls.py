# compare/api_urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("product/<slug:slug>/", views.compare_product_api, name="compare_product_api"),
    path("table/", views.compare_table_api, name="compare_table_api"),
]
