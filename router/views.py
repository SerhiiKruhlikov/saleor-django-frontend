# router/views.py
import logging
from django.http import Http404
from categories.views import detail as category_detail
from products.views import detail as product_detail
from .services import resolve_slug, parse_filter_url

logger = logging.getLogger(__name__)


def dynamic_router(request, slug, filter_path=None):
    language = request.LANGUAGE_CODE

    # If the URL contains /filter/, just pass through to category_detail;
    # filters will be parsed inside detail().
    if '/filter/' in request.path_info:
        return category_detail(request, slug)

    entity_type = resolve_slug(slug, language)
    if entity_type == "product":
        return product_detail(request, slug=slug)
    elif entity_type == "category":
        return category_detail(request, slug=slug)
    else:
        raise Http404("Page not found")
