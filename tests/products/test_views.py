# tests/products/test_views.py
from unittest.mock import patch
from django.urls import reverse
from gateway.saleor.client import SaleorUnavailable


def test_detail_renders_product(client):
    """
    A valid product renders with its name, description and breadcrumbs.
    """
    fake_product = {
        "id": "1",
        "name": "Test Product",
        "slug": "test-product",
        "description": "<p>Hello</p>",
        "category": {"id": "1", "name": "Catalog", "slug": "catalog"},
    }
    fake_breadcrumbs = [{"name": "Catalog", "url": "/catalog/"}]

    with patch("products.views.get_product_by_slug", return_value=fake_product), \
         patch("products.views.get_breadcrumbs_for_product", return_value=fake_breadcrumbs):
        url = reverse("products:detail", kwargs={"slug": "test-product"})
        response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Test Product" in content
    assert "<p>Hello</p>" in content
    assert "Catalog" in content


def test_detail_shows_error_when_saleor_unavailable(client):
    """
    When Saleor is unavailable, a friendly error message is shown.
    """
    with patch("products.views.get_product_by_slug",
               side_effect=SaleorUnavailable("Connection refused")):
        url = reverse("products:detail", kwargs={"slug": "test-product"})
        response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Product temporarily unavailable" in content


def test_detail_returns_404_when_not_found(client):
    """
    A non-existent product slug results in a 404 error.
    """
    with patch("products.views.get_product_by_slug", return_value=None):
        url = reverse("products:detail", kwargs={"slug": "nonexistent"})
        response = client.get(url)

    assert response.status_code == 404


def test_detail_handles_missing_description(client):
    """
    A product without description still renders without errors.
    """
    fake_product = {
        "id": "2",
        "name": "No Description",
        "slug": "no-desc",
        "description": None,
        "category": None,
    }
    with patch("products.views.get_product_by_slug", return_value=fake_product), \
         patch("products.views.get_breadcrumbs_for_product", return_value=[]):
        url = reverse("products:detail", kwargs={"slug": "no-desc"})
        response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "No Description" in content
    assert "No description available." in content


def test_detail_uses_custom_404_page(client):
    """
    When a product is not found, the custom 404 page is used
    (detected via the "Product not found" message).
    """
    with patch("products.views.get_product_by_slug", return_value=None):
        url = reverse("products:detail", kwargs={"slug": "nonexistent"})
        response = client.get(url)

    assert response.status_code == 404
    content = response.content.decode()
    # Проверяем, что используется именно products/404.html
    assert "Product not found" in content
    assert "The product you are looking for does not exist or has been removed." in content
