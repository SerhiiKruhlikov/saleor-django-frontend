# tests/categories/test_views.py
from unittest.mock import patch
from django.urls import reverse
from gateway.saleor.client import SaleorUnavailable


def test_index_renders_with_category_and_tree(client):
    """
    When Saleor returns a valid root category and tree,
    the index page renders without error flags and includes the category name.
    """
    fake_category = {"id": "1", "name": "Catalog", "slug": "catalog", "parent": None}
    fake_tree = [
        {
            "id": "1",
            "name": "Catalog",
            "slug": "catalog",
            "children": [],
            "parent_node": None,
        }
    ]

    with patch("categories.views.get_category_by_slug", return_value=fake_category), \
         patch("categories.views.get_full_tree", return_value=fake_tree), \
         patch("categories.views.find_node_in_tree", return_value=fake_tree[0]), \
         patch("categories.views.get_breadcrumbs_for_category", return_value=[]):
        url = reverse("categories:root")
        response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Catalog" in content
    # No error message should appear
    assert "Catalog temporarily unavailable" not in content


def test_index_shows_error_when_category_unavailable(client):
    """
    When get_category_by_slug returns None, the index page shows an error
    message and does not try to render the category tree.
    """
    with patch("categories.views.get_category_by_slug", return_value=None), \
         patch("categories.views.get_full_tree") as mock_tree, \
         patch("categories.views.get_breadcrumbs_for_category", return_value=[]):
        url = reverse("categories:root")
        response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    # The error message should appear
    assert "Catalog temporarily unavailable" in content
    # The tree should NOT be fetched
    mock_tree.assert_not_called()


def test_detail_renders_category_and_subcategories(client):
    """
    A valid category with subcategories renders successfully,
    showing the category name, parent link, and breadcrumbs.
    """
    fake_category = {
        "id": "2",
        "name": "Video Walls",
        "slug": "video-walls",
        "parent": {"id": "1", "name": "Catalog", "slug": "catalog"},
    }
    fake_tree = [{"id": "1", "children": [fake_category]}]
    fake_node = fake_category  # simplified

    with patch("categories.views.get_category_by_slug", return_value=fake_category), \
         patch("categories.views.get_full_tree", return_value=fake_tree), \
         patch("categories.views.find_node_in_tree", return_value=fake_node), \
         patch("categories.views.get_breadcrumbs_for_category",
               return_value=[{"name": "Catalog", "url": "/catalog/"}]):
        url = reverse("categories:detail", kwargs={"slug": "video-walls"})
        response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Video Walls" in content
    # Parent link should be present
    assert "Back to" in content
    # Breadcrumbs should include the parent
    assert "Catalog" in content


def test_detail_returns_404_when_not_found(client):
    """
    A non-existent category slug results in a 404 error.
    """
    with patch("categories.views.get_category_by_slug", return_value=None):
        url = reverse("categories:detail", kwargs={"slug": "nonexistent"})
        response = client.get(url)

    assert response.status_code == 404


def test_detail_shows_error_when_saleor_unavailable(client):
    """
    When Saleor is unavailable, the detail view renders a friendly error page
    without a 404.
    """
    with patch("categories.views.get_category_by_slug",
               side_effect=SaleorUnavailable("Connection refused")):
        url = reverse("categories:detail", kwargs={"slug": "video-walls"})
        response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Subcategories are temporarily unavailable" in content
