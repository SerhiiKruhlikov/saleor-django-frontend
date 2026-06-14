# tests/categories/test_services.py
from unittest.mock import patch
from categories.services.categories import get_category_count, get_category_by_slug, get_all_categories, get_full_tree, build_category_tree, find_node_in_tree, invalidate_global_category_cache


def test_get_category_count_returns_value():
    """
    Test that get_category_count returns the number from Saleor
    when the query succeeds.
    """
    # 1. Arrange: mock safe_execute_query to return a fake response
    fake_data = {"categories": {"totalCount": 5}}
    with patch("categories.services.categories.safe_execute_query", return_value=fake_data):
        # 2. Act: call the function
        count = get_category_count()

    # 3. Assert: we should get 5
    assert count == 5


def test_get_category_count_returns_zero_on_error():
    """
    Test that get_category_count returns 0 when Saleor is unavailable.
    """
    from gateway.saleor.client import SaleorUnavailable

    # Arrange: safe_execute_query raises SaleorUnavailable
    with patch("categories.services.categories.safe_execute_query",
               side_effect=SaleorUnavailable("Connection error")):
        # Act: call the function
        count = get_category_count()

    # Assert: we should get 0
    assert count == 0


def test_get_category_by_slug_returns_category():
    """Returns a category when Saleor responds with valid data."""
    fake_category = {"id": "1", "name": "Test", "slug": "test"}
    with patch("categories.services.categories.safe_execute_query",
               return_value={"category": fake_category}):
        result = get_category_by_slug("test")

    assert result == fake_category


def test_get_category_by_slug_returns_none_when_not_found():
    """Returns None when Saleor returns null for the category."""
    with patch("categories.services.categories.safe_execute_query",
               return_value={"category": None}):
        result = get_category_by_slug("nonexistent")

    assert result is None


def test_get_category_by_slug_returns_none_on_error():
    """Returns None (without caching) when Saleor is unavailable."""
    from gateway.saleor.client import SaleorUnavailable

    with patch("categories.services.categories.cache") as mock_cache, \
         patch("categories.services.categories.safe_execute_query",
               side_effect=SaleorUnavailable("Network error")):
        mock_cache.get.return_value = None
        result = get_category_by_slug("test")

    assert result is None


def test_get_all_categories_returns_list():
    """Returns a flat list of categories on success."""
    fake_edges = [
        {"node": {"id": "1", "name": "A", "slug": "a", "parent": None}},
        {"node": {"id": "2", "name": "B", "slug": "b", "parent": {"id": "1"}}},
    ]
    # Мокаем safe_execute_query, чтобы он вернул нужные данные
    with patch("categories.services.categories.safe_execute_query",
               return_value={"categories": {"edges": fake_edges}}):
        result = get_all_categories(first=10)

    assert len(result) == 2
    assert result[0]["name"] == "A"


def test_get_all_categories_returns_empty_list_on_error():
    """Returns an empty list when Saleor is unavailable."""
    from gateway.saleor.client import SaleorUnavailable

    with patch("categories.services.categories.cache") as mock_cache, \
         patch("categories.services.categories.safe_execute_query",
               side_effect=SaleorUnavailable("Timeout")):
        mock_cache.get.return_value = None
        # Для get_category_count, которая тоже вызывается внутри, ставим заглушку
        with patch("categories.services.categories.get_category_count",
                   return_value=10):
            result = get_all_categories(first=10)

    assert result == []


def test_get_full_tree_returns_tree():
    """Returns a category tree when flat data is available."""
    fake_flat = [
        {"id": "1", "name": "Root", "slug": "root", "parent": None},
        {"id": "2", "name": "Child", "slug": "child", "parent": {"id": "1"}},
    ]

    with patch("categories.services.categories.get_all_categories",
               return_value=fake_flat):
        tree = get_full_tree()

    # Should have 1 root node
    assert len(tree) == 1
    root = tree[0]
    assert root["name"] == "Root"
    # Root should have one child
    assert len(root["children"]) == 1
    assert root["children"][0]["name"] == "Child"


def test_get_full_tree_returns_empty_list_when_no_data():
    """Returns an empty list when get_all_categories returns nothing."""
    with patch("categories.services.categories.cache") as mock_cache, \
         patch("categories.services.categories.get_all_categories",
               return_value=[]):
        mock_cache.get.return_value = None
        mock_cache.get_or_set.return_value = None
        tree = get_full_tree()

    assert tree == []


def test_build_category_tree_creates_nested_structure():
    """Converts a flat list into a tree with children."""
    flat = [
        {"id": "1", "name": "Root", "slug": "root", "parent": None},
        {"id": "2", "name": "Child", "slug": "child", "parent": {"id": "1"}},
        {"id": "3", "name": "Grandchild", "slug": "grandchild", "parent": {"id": "2"}},
    ]
    tree = build_category_tree(flat)

    # One root
    assert len(tree) == 1
    root = tree[0]
    assert root["name"] == "Root"
    assert root["parent_node"] is None

    # One child under root
    assert len(root["children"]) == 1
    child = root["children"][0]
    assert child["name"] == "Child"
    assert child["parent_node"] is root

    # One grandchild under child
    assert len(child["children"]) == 1
    grandchild = child["children"][0]
    assert grandchild["name"] == "Grandchild"
    assert grandchild["parent_node"] is child


def test_find_node_in_tree_finds_existing_node():
    """Returns the node when the slug exists in the tree."""
    tree = [
        {
            "id": "1",
            "name": "Root",
            "slug": "root",
            "children": [
                {
                    "id": "2",
                    "name": "Child",
                    "slug": "child",
                    "children": [],
                }
            ],
        }
    ]
    node = find_node_in_tree("child", tree)
    assert node is not None
    assert node["name"] == "Child"


def test_find_node_in_tree_returns_none_for_missing_slug():
    """Returns None when the slug is not found."""
    tree = [{"id": "1", "name": "Root", "slug": "root", "children": []}]
    node = find_node_in_tree("nonexistent", tree)
    assert node is None


def test_invalidate_global_category_cache_deletes_keys():
    """Test that global cache keys and patterns are deleted."""
    with patch("categories.services.categories.cache") as mock_cache:
        from categories.services.categories import invalidate_global_category_cache
        invalidate_global_category_cache()

    # Verify that delete was called with specific keys
    mock_cache.delete.assert_any_call("category_total_count")
    mock_cache.delete.assert_any_call("full_category_tree")
    # Verify that delete_pattern was called for all_categories_*
    mock_cache.delete_pattern.assert_called_once_with("all_categories_*")

