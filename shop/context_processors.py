# shop/context_processors.py
from categories.services.categories import get_full_tree


def main_menu(request):
    category_tree = get_full_tree()

    menu_links = [
        {"name": "Головна", "url": "/", "slug": "home"},
        {"name": "Про нас", "url": "/about/", "slug": "about"},
        {"name": "Контакти", "url": "/contacts/", "slug": "contacts"},
    ]

    context = {
        "menu_category_tree": category_tree,
        "menu_links": menu_links,
    }

    return context
