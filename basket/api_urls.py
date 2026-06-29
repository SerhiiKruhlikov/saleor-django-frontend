# basket/api_urls.py
from django.urls import path
from . import views

app_name = 'basket_api'

urlpatterns = [
    path("snapshots/", views.basket_snapshots_api, name="basket_snapshots_api"),
    path("table/", views.basket_table_api, name="basket_table_api"),
    path("checkout/table/", views.checkout_table_api, name="checkout_table_api"),
    path("checkout/create/", views.checkout_create, name="checkout_create"),
]
