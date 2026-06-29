# orders/urls.py
from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("<str:order_id>/", views.order_detail, name="order_detail"),
]
