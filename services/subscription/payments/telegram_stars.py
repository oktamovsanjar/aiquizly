"""
Telegram Stars payment handler.

Telegram Stars is the native in-app currency for Telegram bots.
The bot calls bot.send_invoice() using the payload produced here,
then calls /payments/stars/complete once the pre-checkout is confirmed.

Pricing (approximate at ~$0.013 / star, target USD prices):
  Premium monthly  = $6.99  ≈ 549  stars
  Premium yearly   = $59.99 ≈ 4719 stars
"""

import json
import os
import time
import uuid
from typing import Any

# Stars prices per plan/period
STARS_PRICES: dict[str, dict[str, int]] = {
    "premium": {
        "monthly": 549,
        "yearly": 4719,
    },
    "business": {
        "monthly": 1999,
        "yearly": 17990,
    },
}

# Subscription duration in days
PERIOD_DAYS: dict[str, int] = {
    "monthly": 30,
    "yearly": 365,
}

BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")


def generate_invoice_payload(
    user_id: str,
    plan_name: str,
    period: str,
) -> dict[str, Any]:
    """
    Build the parameters for Telegram's sendInvoice method.

    The bot forwards these directly to the Telegram Bot API.
    `payload` is an opaque string we can verify on the webhook.

    Returns a dict with all fields needed for bot.send_invoice().
    """
    prices = STARS_PRICES.get(plan_name)
    if prices is None:
        raise ValueError(f"Unknown plan: {plan_name}")
    if period not in prices:
        raise ValueError(f"Unknown period '{period}' for plan '{plan_name}'")

    stars_amount = prices[period]
    order_id = str(uuid.uuid4())

    # Opaque payload stored by Telegram; we receive it back on successful payment
    payload_data = {
        "order_id": order_id,
        "user_id": user_id,
        "plan": plan_name,
        "period": period,
        "stars": stars_amount,
        "ts": int(time.time()),
    }
    payload_str = json.dumps(payload_data, separators=(",", ":"))

    plan_labels = {"premium": "Premium", "business": "Business"}
    period_labels = {"monthly": "oylik / monthly", "yearly": "yillik / yearly"}

    return {
        "title": f"Quiz Bot {plan_labels.get(plan_name, plan_name)} — {period_labels.get(period, period)}",
        "description": (
            "Cheksiz fayl yuklash, cheksiz savol, guruhga ulashish va boshqa "
            "premium imkoniyatlar."
        ),
        "payload": payload_str,
        "currency": "XTR",  # Telegram Stars currency code
        "prices": [
            {
                "label": f"{plan_labels.get(plan_name, plan_name)} {period}",
                "amount": stars_amount,
            }
        ],
        # provider_token is empty string for Stars (native Telegram payments)
        "provider_token": "",
        "_meta": {
            "order_id": order_id,
            "plan": plan_name,
            "period": period,
            "days": PERIOD_DAYS.get(period, 30),
            "stars": stars_amount,
        },
    }


def verify_payment(provider_payment_id: str) -> bool:
    """
    Verify that the Stars payment ID looks legitimate.

    For Telegram Stars, Telegram itself guarantees payment authenticity
    via the pre-checkout query mechanism — the bot must confirm the
    pre-checkout before any money is deducted.  By the time this function
    is called (after answerPreCheckoutQuery succeeded), the payment is
    already authorised by Telegram.

    We do a basic non-empty / format sanity check here.
    Full cryptographic verification is handled by the Telegram Bot API
    at the pre-checkout stage.
    """
    if not provider_payment_id or not isinstance(provider_payment_id, str):
        return False
    # Telegram Stars payment IDs are non-empty strings; reject obvious garbage
    if len(provider_payment_id) < 4:
        return False
    return True


def decode_payload(payload_str: str) -> dict[str, Any]:
    """Parse the opaque payload string we embedded in the invoice."""
    try:
        return json.loads(payload_str)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Invalid Stars payload: {exc}") from exc
