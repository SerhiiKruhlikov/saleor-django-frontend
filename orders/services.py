# orders/services.py
import logging
from django.conf import settings
from gateway.saleor.client import safe_execute_query, SaleorUnavailable
from gateway.saleor.loader import load_query

logger = logging.getLogger(__name__)

APP_NAME = "orders"


def get_order(order_id: str) -> dict | None:
    """Fetch order details from Saleor by ID."""
    try:
        query = load_query(APP_NAME, "queries/order_by_id.graphql")
        data = safe_execute_query(query, {"id": order_id})
        if data is None:
            return None
        return data.get("order")
    except SaleorUnavailable:
        logger.warning("Saleor unavailable while fetching order %s", order_id)
        return None
