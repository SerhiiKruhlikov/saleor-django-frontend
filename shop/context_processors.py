# shop/context_processors.py
from django.conf import settings

from categories.services.categories import get_full_tree
import logging

logger = logging.getLogger(__name__)


def main_menu(request):
    try:
        category_tree = get_full_tree()
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
    }
