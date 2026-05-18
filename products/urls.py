# products/urls.py
from django.urls import path

from products.views import detail

app_name = 'products'


urlpatterns = [
    path('<slug:slug>/', detail, name='detail'),
]
