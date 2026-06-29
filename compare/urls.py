# compare/urls.py
from django.urls import path
from . import views

app_name = "compare"

urlpatterns = [
    path("", views.compare_page, name="compare_page"),
]
