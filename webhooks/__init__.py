# webhooks/__init__.py
"""
Webhook receiver and dispatch system.

Saleor sends webhook notifications (GraphQL subscriptions) to a single
endpoint.  This package:

1. **Verifies** the request signature (if a secret is configured).
2. **Parses** the JSON payload and extracts the ``__typename``.
3. **Dispatches** the event to the appropriate application handler
   via the registry in :mod:`webhooks.handlers`.

Adding a new entity (e.g., products) requires three steps:

- Create ``<app>/webhooks.py`` with a handler function.
- Register the handler in :data:`webhooks.handlers.EVENT_HANDLERS`.
- Configure the corresponding webhook in the Saleor Dashboard
  (Settings → Webhooks).
"""