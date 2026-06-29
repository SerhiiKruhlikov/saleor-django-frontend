# app/urls.py
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path

from shop.views import custom_404
from webhooks import views as webhooks_views
from compare import views as compare_views

handler404 = custom_404

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhooks/', include('webhooks.urls')),
    path('api/compare/', include('compare.api_urls')),
    path('api/products/', include('products.api_urls')),
    path('api/basket/', include('basket.api_urls')),
]

# Мультиязычные маршруты (основной сайт)
urlpatterns += i18n_patterns(
    path('order/', include('orders.urls')),
    path('compare/', include(('compare.urls', 'compare'), namespace='compare')),
    path('basket/', include(('basket.urls', 'basket'), namespace='basket')),
    path('', include(('shop.urls', 'shop'), namespace='shop')),
    path('', include(('router.urls', 'router'), namespace='router')),
    prefix_default_language=False,
)

if settings.DEBUG:
    if getattr(settings, 'DOCS', False):
        urlpatterns += [
            path('docs/', include('docs.urls')),
        ]
