# gateway/saleor/client.py
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)   # gateway.saleor.client


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

    Raises:
        SaleorUnavailable: When Saleor cannot be reached or returns
            an error response.
    """
    try:
        return execute_query(query, variables)
    except requests.Timeout:
        logger.warning("Saleor query timed out")
        raise SaleorUnavailable("Saleor query timed out")
    except requests.ConnectionError:
        logger.warning("Cannot connect to Saleor")
        raise SaleorUnavailable("Cannot connect to Saleor")
    except requests.HTTPError as e:
        logger.warning("Saleor HTTP error: %s", e)
        raise SaleorUnavailable(f"Saleor HTTP error: {e}")
    except Exception as e:
        logger.warning("Saleor query failed: %s", e)
        raise SaleorUnavailable(f"Saleor query failed: {e}")
