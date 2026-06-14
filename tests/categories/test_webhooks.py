# tests/categories/test_webhooks.py
from unittest.mock import patch
from categories.webhooks import handle_category_event


def test_handle_category_event_invalidates_specific_and_global_cache():
    """
    Test that handle_category_event deletes the specific category slug key
    and calls invalidate_global_category_cache.
    """
    payload = {"category": {"slug": "test-slug"}}
    event_type = "CategoryUpdated"

    with patch("categories.webhooks.cache.delete") as mock_delete, \
         patch("categories.webhooks.invalidate_global_category_cache") as mock_invalidate:

        handle_category_event(event_type, payload)

    # Assert that the specific key is deleted
    mock_delete.assert_called_once_with("category_slug_test-slug")
    # Assert that global cache is invalidated
    mock_invalidate.assert_called_once()


def test_handle_category_event_without_slug():
    """
    Test that handle_category_event still invalidates global cache
    even when the payload does not contain a category slug.
    """
    payload = {}
    event_type = "CategoryUpdated"

    with patch("categories.webhooks.cache.delete") as mock_delete, \
         patch("categories.webhooks.invalidate_global_category_cache") as mock_invalidate:

        handle_category_event(event_type, payload)

    # Specific delete should not be called
    mock_delete.assert_not_called()
    # Global invalidation should still happen
    mock_invalidate.assert_called_once()
