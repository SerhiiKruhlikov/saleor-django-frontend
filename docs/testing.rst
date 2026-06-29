.. docs/testing.rst

Testing
=======

The project uses **pytest** with the **pytest-django** plugin.
Tests are located in the ``tests/`` directory at the project root.

Test layout
-----------

.. code-block:: text

    tests/
    ├── conftest.py                    # Pytest configuration, cache isolation
    ├── categories/
    │   ├── test_services.py          # Unit tests for category services
    │   ├── test_webhooks.py          # Unit tests for category webhook handlers
    │   └── test_views.py             # View tests (index, detail, error cases)

Running tests
-------------

Run all tests::

    pytest

Run a single test file::

    pytest tests/categories/test_services.py -v

Run a specific test::

    pytest tests/categories/test_services.py::test_get_category_count_returns_value -v

Cache safety during tests
--------------------------

Tests use ``LocMemCache`` to avoid depending on Redis.
The cache is automatically cleared before each test via the
``conftest.py`` fixture.