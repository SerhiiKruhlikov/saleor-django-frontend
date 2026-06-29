# basket/services.py
import logging
from django.conf import settings
from gateway.saleor.loader import load_query

logger = logging.getLogger(__name__)

APP_NAME = "basket"


def create_order(email: str, address_data: dict, items: list[dict]) -> dict:
    """
    Create an order in Saleor using the Checkout flow.
    """
    from gateway.saleor.client import safe_execute_query
    from django.conf import settings

    channel = settings.SALEOR_CHANNEL

    # 1. Создаём корзину
    query = load_query(APP_NAME, "queries/checkout_create.graphql")
    lines = [{"variantId": item["variant_id"], "quantity": item["quantity"]} for item in items]
    variables = {
        "input": {
            "channel": channel,
            "email": email,
            "lines": lines,
        }
    }
    data = safe_execute_query(query, variables)
    if data is None:
        return {"success": False, "error": "Saleor unavailable"}

    errors = data.get("checkoutCreate", {}).get("errors", [])
    if errors:
        return {"success": False, "error": f"Checkout create error: {errors[0].get('message')}"}

    checkout_id = data["checkoutCreate"]["checkout"]["id"]

    # 2. Обновляем адрес доставки
    query = load_query(APP_NAME, "queries/checkout_shipping_address_update.graphql")
    address_vars = {
        "id": checkout_id,
        "address": {
            "firstName": address_data.get("firstName"),
            "lastName": address_data.get("lastName"),
            "phone": address_data.get("phone"),
            "city": address_data.get("city"),
            "streetAddress1": address_data.get("streetAddress1"),
            "postalCode": address_data.get("postalCode", ""),
            "country": address_data.get("country", "UA"),
        }
    }
    data = safe_execute_query(query, address_vars)
    if data is None:
        return {"success": False, "error": "Saleor unavailable"}

    errors = data.get("checkoutShippingAddressUpdate", {}).get("errors", [])
    if errors:
        return {"success": False, "error": f"Address update error: {errors[0].get('message')}"}

    # 2.5 Обновляем платёжный адрес (используем тот же адрес)
    query = load_query(APP_NAME, "queries/checkout_billing_address_update.graphql")
    data = safe_execute_query(query, address_vars)  # те же переменные, что и для shipping
    if data is None:
        return {"success": False, "error": "Saleor unavailable"}

    errors = data.get("checkoutBillingAddressUpdate", {}).get("errors", [])
    if errors:
        return {"success": False, "error": f"Billing address update error: {errors[0].get('message')}"}

    # 3. Завершаем оформление
    query = load_query(APP_NAME, "queries/checkout_complete.graphql")
    data = safe_execute_query(query, {"id": checkout_id})
    if data is None:
        return {"success": False, "error": "Saleor unavailable"}

    errors = data.get("checkoutComplete", {}).get("errors", [])
    if errors:
        return {"success": False, "error": f"Checkout complete error: {errors[0].get('message')}"}

    order_id = data["checkoutComplete"]["order"]["id"]
    return {"success": True, "order_id": order_id}
