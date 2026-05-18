import requests
from django.conf import settings


def execute_query(query: str, variables: dict = None) -> dict:
    headers = {}

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
