# router/views.py
import logging
from django.http import Http404
from categories.views import detail as category_detail
from products.views import detail as product_detail
from .services import resolve_slug

logger = logging.getLogger(__name__)


def dynamic_router(request, slug):
    """
    Resolve a short URL slug to a product, category, or other entity.

    Uses :func:`~router.services.resolve_slug` which checks a cache,
    then queries Saleor for a product or a category.  If the slug is
    identified, the request is forwarded to the appropriate detail view.
    Otherwise a 404 is raised.
    """
    language = request.LANGUAGE_CODE
    entity_type = resolve_slug(slug, language)

    if entity_type == "product":
        return product_detail(request, slug=slug)
    elif entity_type == "category":
        return category_detail(request, slug=slug)
    else:
        logger.info("Slug not resolved: %s (lang=%s)", slug, language)
        raise Http404("Page not found")
