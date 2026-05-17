"""
Payme payment handler for Uzbekistan.

Payme (payme.uz) uses a JSON-RPC 2.0 protocol over HTTPS.
The merchant server must implement three methods:
  CheckPerformTransaction
  CreateTransaction
  PerformTransaction

For the subscription service we expose a simplified interface:
  - create_invoice()      → returns a redirect URL the user visits to pay
  - check_payment_status()→ queries Payme for a transaction's state
  - verify_payme_signature() → validates the Authorization header from Payme webhooks

Environment variables required:
  PAYME_MERCHANT_ID      – your merchant ID from Payme cabinet
  PAYME_MERCHANT_KEY     – secret key (used for Basic Auth and signature checks)
  PAYME_BASE_URL         – checkout base URL (default: https://checkout.paycom.uz)
  PAYME_API_URL          – server-to-server API URL
"""
import base64
import hashlib
import hmac
import json
import os
from typing import Any

import httpx

PAYME_MERCHANT_ID: str = os.getenv("PAYME_MERCHANT_ID", "")
PAYME_MERCHANT_KEY: str = os.getenv("PAYME_MERCHANT_KEY", "")
PAYME_BASE_URL: str = os.getenv("PAYME_BASE_URL", "https://checkout.paycom.uz")
PAYME_API_URL: str = os.getenv("PAYME_API_URL", "https://checkout.paycom.uz/api")

# Payme transaction state codes
_PAYME_STATE_CREATED = 1
_PAYME_STATE_COMPLETED = 2
_PAYME_STATE_CANCELLED = -1
_PAYME_STATE_CANCELLED_AFTER_COMPLETE = -2


def create_invoice(
    user_id: str,
    amount_uzs: int,
    order_id: str,
) -> str:
    """
    Build a Payme checkout URL.

    Payme's redirect-based flow: encode the merchant ID + order params as
    Base64, append to the checkout base URL, and redirect the user.

    `amount_uzs` is in UZS tiyin (1 UZS = 100 tiyin).
    The function expects the value already in tiyin (multiply UZS × 100).

    Returns the checkout URL string.
    """
    if not PAYME_MERCHANT_ID:
        raise RuntimeError("PAYME_MERCHANT_ID environment variable is not set")

    params = {
        "m": PAYME_MERCHANT_ID,
        "ac.order_id": order_id,
        "ac.user_id": user_id,
        "a": amount_uzs,   # amount in tiyin
        "l": "uz",         # language
    }
    # Payme encodes params as key=value pairs joined by ";" then base64-encodes
    param_str = ";".join(f"{k}={v}" for k, v in params.items())
    encoded = base64.b64encode(param_str.encode()).decode()
    return f"{PAYME_BASE_URL}/{encoded}"


async def check_payment_status(order_id: str) -> str:
    """
    Query Payme's server API for the transaction linked to `order_id`.

    Returns one of: 'pending', 'completed', 'failed'
    """
    if not PAYME_MERCHANT_KEY:
        raise RuntimeError("PAYME_MERCHANT_KEY environment variable is not set")

    payload = {
        "id": 1,
        "method": "CheckTransaction",
        "params": {"id": order_id},
    }
    auth = base64.b64encode(
        f"Paycom:{PAYME_MERCHANT_KEY}".encode()
    ).decode()
    headers = {
        "X-Auth": f"{PAYME_MERCHANT_ID}:{PAYME_MERCHANT_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            PAYME_API_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    result = data.get("result", {})
    state = result.get("state")

    if state == _PAYME_STATE_COMPLETED:
        return "completed"
    if state in (_PAYME_STATE_CANCELLED, _PAYME_STATE_CANCELLED_AFTER_COMPLETE):
        return "failed"
    # state == 1 (created/pending) or unknown
    return "pending"


def verify_payme_signature(request_body: bytes, merchant_key: str) -> bool:
    """
    Verify the Authorization header sent by Payme on webhook callbacks.

    Payme sends: Authorization: Basic base64(Paycom:<merchant_key>)

    `request_body` is the raw bytes of the Authorization header value
    (just the base64 part after "Basic ").

    Returns True if the provided credentials match our merchant key.
    """
    try:
        decoded = base64.b64decode(request_body).decode()
        # Expected format: "Paycom:<merchant_key>"
        prefix, _, provided_key = decoded.partition(":")
        if prefix != "Paycom":
            return False
        return hmac.compare_digest(provided_key, merchant_key)
    except Exception:
        return False


def parse_webhook_body(raw: bytes) -> dict[str, Any]:
    """Parse Payme's JSON-RPC webhook body."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid Payme webhook body: {exc}") from exc


def build_rpc_error(code: int, message: str, request_id: Any = 1) -> dict[str, Any]:
    """Build a Payme-compatible JSON-RPC error response."""
    return {
        "id": request_id,
        "error": {
            "code": code,
            "message": {"uz": message, "ru": message, "en": message},
        },
    }


def build_rpc_result(result: dict[str, Any], request_id: Any = 1) -> dict[str, Any]:
    """Build a Payme-compatible JSON-RPC success response."""
    return {"id": request_id, "result": result}
