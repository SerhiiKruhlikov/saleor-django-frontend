# router/urls.py
from django.urls import path
from .views import dynamic_router

app_name = "router"

urlpatterns = [
    path("<slug:slug>/", dynamic_router, name="dynamic_router"),
]
