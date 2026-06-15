# app/urls.py
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from webhooks import views as webhooks_views
from shop.views import custom_404

handler404 = custom_404

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhooks/saleor/', webhooks_views.saleor_webhook),
    path('webhooks/', include('webhooks.urls')),
    path('', include(('shop.urls', 'shop'), namespace='shop')),
    path('catalog/', include(('categories.urls', 'categories'), namespace='categories')),
    path('product/', include(('products.urls', 'products'), namespace='products')),
]

if settings.DEBUG:
    if getattr(settings, 'DOCS', False):
        urlpatterns += [
            path('docs/', include('docs.urls')),
        ]
