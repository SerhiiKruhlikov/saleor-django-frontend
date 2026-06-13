# webhooks/views.py
import json
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from .services import verify_saleor_signature
from .handlers import EVENT_HANDLERS


@require_POST
@csrf_exempt
def saleor_webhook(request):
    """
    Handle incoming webhook notifications from Saleor.

    .. important::
       The corresponding webhook **must** be configured in the Saleor
       Dashboard (Settings → Webhooks) with the target URL pointing to
       this view and the following events enabled:

       - ``CategoryCreated``
       - ``CategoryUpdated``
       - ``CategoryDeleted``

       (Add product events when you are ready for product cache
       invalidation.)

    The ``Saleor-Signature`` header is verified only when
    ``SALEOR_WEBHOOK_SECRET`` is set (optional, as the legacy secret
    mechanism is deprecated in recent Saleor versions).
    """
    # 1. Verify signature if a secret key is configured
    if settings.SALEOR_WEBHOOK_SECRET:
        if not verify_saleor_signature(request):
            return HttpResponseForbidden("Invalid signature")

    # 2. Parse JSON payload
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    # 3. Extract event type
    event_type = payload.get("__typename", "")
    if not event_type:
        return HttpResponseBadRequest("Missing __typename")

    # 4. Look up and call the appropriate handler
    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        # Unknown event – log it but do not fail
        print(f"Ignored unknown webhook event: {event_type}")
        return HttpResponse("OK")

    handler(event_type, payload)
    return HttpResponse("OK")
