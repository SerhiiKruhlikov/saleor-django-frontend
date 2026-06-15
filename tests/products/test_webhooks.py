# tests/products/test_webhooks.py
from unittest.mock import patch
from products.webhooks import handle_product_event


def test_handle_product_event_invalidates_slug():
    """
    When the payload contains product.slug, the corresponding cache key
    is deleted.
    """
    payload = {"product": {"slug": "test-product"}}
    event_type = "ProductUpdated"

    with patch("products.webhooks.invalidate_product_cache_by_slug") as mock_invalidate:
        handle_product_event(event_type, payload)

    mock_invalidate.assert_called_once_with("test-product")


def test_handle_product_event_without_slug():
    """
    When the payload does not contain a usable slug, nothing is invalidated
    and a warning is logged.
    """
    payload = {"product": {}}
    event_type = "ProductUpdated"

    with patch("products.webhooks.invalidate_product_cache_by_slug") as mock_invalidate, \
         patch("products.webhooks.logger") as mock_logger:
        handle_product_event(event_type, payload)

    mock_invalidate.assert_not_called()
    mock_logger.warning.assert_called_once()
