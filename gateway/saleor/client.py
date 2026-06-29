# gateway/saleor/client.py
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)   # gateway.saleor.client

# Flag raised when an error occurs, cleared on the first successful request
_saleor_was_unavailable = False


def _on_saleor_became_unavailable():
    """
    Called once when Saleor becomes unavailable (first error after a
    period of normal operation). Invalidates all category and product
    caches so that stale data is not served.
    """
    from categories.services.categories import invalidate_global_category_cache
    from products.services.products import invalidate_all_product_cache
    from router.services import invalidate_global_router_cache
    invalidate_global_category_cache()
    invalidate_all_product_cache()
    invalidate_global_router_cache()
    logger.info("Saleor became unavailable – category cache invalidated")


def _on_saleor_reconnected():
    """
    Called once when Saleor becomes available again after a period of
    unavailability. Invalidates all category and product caches so that
    fresh data can be fetched immediately.
    """
    from categories.services.categories import invalidate_global_category_cache
    from products.services.products import invalidate_all_product_cache
    from router.services import invalidate_global_router_cache
    invalidate_global_category_cache()
    invalidate_all_product_cache()
    invalidate_global_router_cache()
    logger.info("Saleor is back online – category cache invalidated")


class SaleorUnavailable(Exception):
    """Raised when Saleor cannot be reached or returns an error."""
    pass


def execute_query(query: str, variables: dict = None) -> dict:
    """
    Execute a GraphQL query against Saleor and return the 'data' dict.

    Raises:
        requests.HTTPError: On HTTP or GraphQL-level errors.
    """
    headers = {}
    token = getattr(settings, "SALEOR_AUTH_TOKEN", None)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(
        settings.SALEOR_API_URL,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")

    return data["data"]


def safe_execute_query(query: str, variables: dict = None) -> dict | None:
    """
    Execute a GraphQL query safely.

    Returns the ``data`` dictionary on success.

    If the requested entity is not found (Saleor responds with ``null``),
    returns ``None``.  On network errors, timeouts, HTTP errors, or
    GraphQL‑level errors, raises :exc:`SaleorUnavailable` (the original
    exception is logged as a warning).

    Also tracks Saleor availability:
    - When Saleor becomes **unavailable** after being healthy, the category
      cache is invalidated so stale menus are removed.
    - When Saleor becomes **available** again after a period of errors,
      the category cache is invalidated so fresh navigation can be fetched.
    """
    global _saleor_was_unavailable

    try:
        result = execute_query(query, variables)
    except requests.Timeout:
        if not _saleor_was_unavailable:
            _on_saleor_became_unavailable()
        _saleor_was_unavailable = True
        logger.warning("Saleor query timed out")
        raise SaleorUnavailable("Saleor query timed out")
    except requests.ConnectionError:
        if not _saleor_was_unavailable:
            _on_saleor_became_unavailable()
        _saleor_was_unavailable = True
        logger.warning("Cannot connect to Saleor")
        raise SaleorUnavailable("Cannot connect to Saleor")
    except requests.HTTPError as e:
        if not _saleor_was_unavailable:
            _on_saleor_became_unavailable()
        _saleor_was_unavailable = True
        logger.warning("Saleor HTTP error: %s", e)
        raise SaleorUnavailable(f"Saleor HTTP error: {e}")
    except Exception as e:
        if not _saleor_was_unavailable:
            _on_saleor_became_unavailable()
        _saleor_was_unavailable = True
        logger.warning("Saleor query failed: %s", e)
        raise SaleorUnavailable(f"Saleor query failed: {e}")

    # Request succeeded – if Saleor was previously unavailable, invalidate the cache
    if _saleor_was_unavailable and getattr(settings, 'SALEOR_RECONNECT_INVALIDATION_ENABLED', True):
        try:
            _on_saleor_reconnected()
        except Exception:
            logger.exception("Failed to invalidate cache after Saleor reconnection")
    _saleor_was_unavailable = False

    return result
