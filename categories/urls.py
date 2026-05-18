# categories/urls.py
from django.urls import path

from categories.views import index, detail

app_name = 'categories'


urlpatterns = [
    path('', index, {'slug': 'catalog'}, name='root'),
    path('<slug:slug>/', detail, name='detail'),
]
