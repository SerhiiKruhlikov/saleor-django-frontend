# tests/products/test_services.py
from unittest.mock import patch
from products.services.products import get_product_by_slug


def test_get_product_by_slug_returns_product():
    """
    Returns a product dictionary when Saleor responds with valid data.
    """
    fake_product = {
        "id": "1",
        "name": "Test Product",
        "slug": "test-product",
        "description": None,
    }
    with patch("products.services.products.safe_execute_query",
               return_value={"product": fake_product}):
        result = get_product_by_slug("test-product")

    assert result == fake_product


def test_get_product_by_slug_converts_description():
    """
    Editor.js description is converted to HTML when present.
    """
    fake_json = '{"time":123,"blocks":[{"type":"paragraph","data":{"text":"Hello"}}]}'
    fake_product = {
        "id": "1",
        "name": "Test Product",
        "slug": "test-product",
        "description": fake_json,
    }
    with patch("products.services.products.safe_execute_query",
               return_value={"product": fake_product}):
        result = get_product_by_slug("test-product")

    assert result is not None
    assert result["description"] == "<p>Hello</p>"


def test_get_product_by_slug_returns_none_when_not_found():
    """
    Returns None when Saleor returns null for the product.
    """
    with patch("products.services.products.safe_execute_query",
               return_value={"product": None}):
        result = get_product_by_slug("nonexistent")

    assert result is None


def test_get_product_by_slug_returns_none_on_error():
    """
    Returns None (without caching) when Saleor is unavailable.
    """
    from gateway.saleor.client import SaleorUnavailable

    with patch("products.services.products.safe_execute_query",
               side_effect=SaleorUnavailable("Network error")):
        result = get_product_by_slug("test-product")

    assert result is None


def test_get_product_by_slug_returns_none_when_data_is_none():
    """
    Returns None when safe_execute_query itself returns None (no data key).
    """
    with patch("products.services.products.safe_execute_query",
               return_value=None):
        result = get_product_by_slug("test-product")

    assert result is None
