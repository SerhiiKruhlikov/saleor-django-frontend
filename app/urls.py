# app/urls.py
from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.static import serve as static_serve
from django.contrib import admin
from django.urls import path, include, re_path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('shop.urls', 'shop'), namespace='shop')),
    path('catalog/', include(('categories.urls', 'categories'), namespace='categories')),
    path('product/', include(('products.urls', 'products'), namespace='products')),
]

if settings.DEBUG:
    if getattr(settings, 'DOCS', False):
        urlpatterns += [
            path('docs/', include('docs.urls')),
        ]
