# app/urls.py
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path

from shop.views import custom_404
from webhooks import views as webhooks_views

handler404 = custom_404

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhooks/saleor/', webhooks_views.saleor_webhook),
    path('webhooks/', include('webhooks.urls')),
    path('api/products/', include('products.api_urls')),
]

# Мультиязычные маршруты (основной сайт)
urlpatterns += i18n_patterns(
    path('', include(('shop.urls', 'shop'), namespace='shop')),      # Главная
    path('', include(('router.urls', 'router'), namespace='router')),# Динамический роутер
    prefix_default_language=False,
)

if settings.DEBUG:
    if getattr(settings, 'DOCS', False):
        urlpatterns += [
            path('docs/', include('docs.urls')),
        ]
