# compare/services.py
import json
import logging
from django.conf import settings
from django.core.cache import cache
from gateway.saleor.client import safe_execute_query, SaleorUnavailable
from gateway.saleor.loader import load_query

logger = logging.getLogger(__name__)

APP_NAME = "compare"
TIMEOUT = getattr(settings, 'COMPARE_CACHE_TTL', 86400)


def get_product_snapshot(slug: str, language: str | None = None) -> dict | None:
    """
    Return a product snapshot for comparison purposes.

    The result is cached in Redis per language.
    Returns ``None`` if Saleor is unreachable or the product is not found.
    """
    if language is None:
        language = settings.LANGUAGE_CODE

    cache_key = f"compare:{language}:{slug}"
    snapshot = cache.get(cache_key)
    if snapshot is not None:
        return snapshot

    try:
        query = load_query(APP_NAME, "queries/compare_snapshot.graphql")
        variables = {
            "slug": slug,
            "channel": settings.SALEOR_CHANNEL,
            "lang": language.upper(),
        }
        data = safe_execute_query(query, variables)
        if data is None:
            return None

        product = data.get("product")
        if not product:
            return None

        # Apply translation to the product itself
        translation = product.get("translation")
        if translation and translation.get("name"):
            product["name"] = translation["name"]

        # Apply translation to the category (if available)
        category = product.get("category")
        if category:
            cat_trans = category.get("translation")
            if cat_trans and cat_trans.get("name"):
                category["name"] = cat_trans["name"]

        # Extract the status attribute
        status = None
        for attr in product.get("attributes", []):
            attr_obj = attr.get("attribute", {})
            # Apply translation to the attribute name
            attr_trans = attr_obj.get("translation")
            if attr_trans and attr_trans.get("name"):
                attr_obj["name"] = attr_trans["name"]
            if attr_obj.get("slug") == "status":
                values = attr.get("values", [])
                if values:
                    val = values[0]
                    # Apply translation to the value
                    val_trans = val.get("translation")
                    if val_trans and val_trans.get("name"):
                        val["name"] = val_trans["name"]
                    status = {
                        "slug": val["slug"],
                        "name": val.get("name", val["slug"]),
                    }
                break

        # Pricing information
        pricing = product.get("pricing", {})
        price_range = pricing.get("priceRange", {})
        undiscounted_range = pricing.get("priceRangeUndiscounted", {})
        price_amount = None
        price_currency = None
        old_price_amount = None
        if price_range:
            start = price_range.get("start", {}).get("gross", {})
            price_amount = start.get("amount")
            price_currency = start.get("currency")
        if undiscounted_range:
            old_start = undiscounted_range.get("start", {}).get("gross", {})
            old_price_amount = old_start.get("amount")

        # Collect attributes into a flat list
        attributes_list = []
        for attr in product.get("attributes", []):
            attr_obj = attr.get("attribute", {})
            attr_name = attr_obj.get("name", "")
            attr_slug = attr_obj.get("slug", "")
            values = attr.get("values", [])
            val_names = []
            for v in values:
                v_trans = v.get("translation")
                v_name = v_trans["name"] if (v_trans and v_trans.get("name")) else v.get("name", v.get("slug", ""))
                val_names.append(v_name)
            if val_names:
                attributes_list.append({
                    "slug": attr_slug,
                    "name": attr_name,
                    "value": ", ".join(val_names),
                })

        snapshot = {
            "slug": product["slug"],
            "name": product.get("name", ""),
            "thumbnail": product.get("thumbnail", {}).get("url") if product.get("thumbnail") else None,
            "status": status,
            "price": {
                "amount": price_amount,
                "currency": price_currency,
                "before_discount": old_price_amount,
            },
            "attributes": attributes_list,
        }

        cache.set(cache_key, snapshot, timeout=TIMEOUT)
        return snapshot

    except SaleorUnavailable:
        logger.warning("Saleor unavailable while fetching compare snapshot for %s", slug)
        return None
