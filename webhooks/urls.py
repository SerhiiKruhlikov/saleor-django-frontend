# webhooks/urls.py
from django.urls import path
from . import views


"""
URL configuration for the webhooks app.

Maps the ``/webhooks/saleor/`` endpoint to the view that receives
notifications from Saleor.
"""
urlpatterns = [
    path("saleor/", views.saleor_webhook, name="saleor_webhook"),
]
