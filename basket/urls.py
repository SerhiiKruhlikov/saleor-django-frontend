# basket/urls.py
from django.urls import path
from . import views

app_name = "basket"

urlpatterns = [
    path("", views.basket_page, name="basket_page"),
    path('checkout/', views.checkout_page, name='checkout'),
]
