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
from products.webhooks import handle_product_event, handle_promotion_event

# Map Saleor event types to application handler functions
EVENT_HANDLERS = {
    # Categories
    "CategoryCreated": handle_category_event,
    "CategoryUpdated": handle_category_event,
    "CategoryDeleted": handle_category_event,
    # Products
    "ProductCreated": handle_product_event,
    "ProductUpdated": handle_product_event,
    "ProductDeleted": handle_product_event,
    # Promotional Events
    "PromotionCreated": handle_promotion_event,
    "PromotionUpdated": handle_promotion_event,
    "PromotionDeleted": handle_promotion_event,
    "PromotionRuleCreated": handle_promotion_event,
    "PromotionRuleUpdated": handle_promotion_event,
    "PromotionRuleDeleted": handle_promotion_event,
    "PromotionStarted": handle_promotion_event,
    "PromotionEnded": handle_promotion_event,
}
