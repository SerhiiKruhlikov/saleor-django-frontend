# webhooks/services.py
import hmac
import hashlib
from django.conf import settings


def verify_saleor_signature(request) -> bool:
    """
    Verify that the incoming request comes from Saleor.

    Checks the ``Saleor-Signature`` header against the HMAC‑SHA256
    digest of the request body using the secret key configured in
    ``SALEOR_WEBHOOK_SECRET``.

    Args:
        request: Django HttpRequest object.

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    signature = request.headers.get("Saleor-Signature")
    if not signature:
        return False

    secret = settings.SALEOR_WEBHOOK_SECRET.encode()
    body = request.body
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
