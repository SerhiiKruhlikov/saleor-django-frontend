# shop/context_processors.py
import logging
from django.conf import settings
from categories.services.categories import get_full_tree
import gateway.saleor.client as saleor_client

logger = logging.getLogger(__name__)


def main_menu(request):
    """
    Context processor that supplies the main navigation menu.

    Adds ``menu_category_tree`` (the full category tree) and ``menu_links``
    (static links) to the template context.

    A lightweight health‑check query is executed on every request to
    immediately detect when Saleor becomes unavailable or comes back.
    This keeps the category cache and the navigation in sync with the
    actual availability of Saleor.
    """
    # Execute a lightweight query to monitor Saleor availability.
    # If Saleor is down, the first error will trigger cache invalidation
    # so that the menu disappears.  Once Saleor is back, the first
    # successful request will invalidate the cache again and the menu
    # will be rebuilt with fresh data.
    try:
        saleor_client.safe_execute_query("{ shop { name } }")
    except Exception:
        # Still unavailable – continue without a menu
        pass

    try:
        category_tree = get_full_tree(language=request.LANGUAGE_CODE)
    except Exception as e:
        logger.warning("Failed to load category tree for menu: %s", e)
        category_tree = []

    menu_links = [
        {"name": "Головна", "url": "/", "slug": "home"},
        {"name": "Про нас", "url": "/about/", "slug": "about"},
        {"name": "Контакти", "url": "/contacts/", "slug": "contacts"},
    ]

    return {
        "menu_category_tree": category_tree,
        "menu_links": menu_links,
        "LOCALSTORAGE_PREFIX": getattr(settings, "LOCALSTORAGE_PREFIX", "sdf"),
        "currency": getattr(settings, "SALEOR_DEFAULT_CURRENCY", "UAH"),
    }