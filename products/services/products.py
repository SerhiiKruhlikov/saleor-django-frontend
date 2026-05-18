# products/services/products.py
import json

from gateway.saleor.client import execute_query
from gateway.saleor.loader import load_query

APP_NAME = "products"


def get_product_by_slug(slug: str) -> dict:
    query = load_query(APP_NAME, "queries/product_by_slug.graphql")
    variables = {"slug": slug}
    data = execute_query(query, variables)
    product = data.get("product")

    if product and product.get("description"):
        product["description"] = editorjs_to_html(product["description"])

    return data["product"]


def editorjs_to_html(description_json) -> str:
    try:
        data = json.loads(description_json)
    except (json.JSONDecodeError, TypeError):
        return description_json or ""

    blocks = data.get("blocks", [])
    html_parts = []

    for block in blocks:
        block_type = block.get("type", "")
        block_data = block.get("data", {})

        if block_type == "paragraph":
            text = block_data.get("text", "")
            html_parts.append(f"<p>{text}</p>")

        elif block_type == "header":
            text = block_data.get("text", "")
            level = block_data.get("level", 2)
            level = max(1, min(level, 6))
            html_parts.append(f"<h{level}>{text}</h{level}>")

    return "\n".join(html_parts)
