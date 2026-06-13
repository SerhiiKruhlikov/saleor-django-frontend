# webhooks/handlers.py
"""
Central registry that maps Saleor event types to handler functions.

Each key is the ``__typename`` string sent by Saleor (e.g.
``"CategoryCreated"``).  The corresponding value is a callable with the
signature ``handler(event_type: str, payload: dict)``.

To add support for a new entity:

1. Create a ``webhooks.py`` file in the relevant Django app.
2. Define a handler function that performs the necessary cache
   invalidation or other side effects.
3. Import the handler here and add an entry to ``EVENT_HANDLERS``.
"""
from categories.webhooks import handle_category_event

# Map Saleor event types to application handler functions
EVENT_HANDLERS = {
    "CategoryCreated": handle_category_event,
    "CategoryUpdated": handle_category_event,
    "CategoryDeleted": handle_category_event,
    # Future additions:
    # "ProductCreated": handle_product_event,
    # ...
}