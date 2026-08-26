"""WhatsApp payment reminders — Cloud API when configured, otherwise wa.me links."""
from __future__ import annotations

from decimal import Decimal
from urllib.parse import quote

import httpx

from app.core.config import settings


def normalize_whatsapp_number(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = "91" + digits[1:]
    if len(digits) == 10:
        digits = "91" + digits
    if len(digits) < 11:
        return None
    return digits


def reminder_message(*, org_name: str, farmer_name: str, amount: Decimal) -> str:
    return (
        f"Namaste {farmer_name}, this is {org_name}. "
        f"Your khata outstanding is Rs.{Decimal(amount):.2f}. "
        f"Please settle at your convenience. Thank you."
    )


def wa_me_link(phone: str | None, text: str) -> str | None:
    num = normalize_whatsapp_number(phone)
    if not num:
        return None
    return f"https://wa.me/{num}?text={quote(text)}"


def cloud_api_configured() -> bool:
    return bool(settings.whatsapp_token and settings.whatsapp_phone_number_id)


def send_whatsapp_text(phone: str, text: str, *, farmer_name: str = "", amount: Decimal | None = None) -> tuple[bool, str]:
    if not cloud_api_configured():
        return False, "WhatsApp Cloud API is not configured"
    num = normalize_whatsapp_number(phone)
    if not num:
        return False, "Invalid mobile number"
    url = f"https://graph.facebook.com/v21.0/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    if settings.whatsapp_template_name:
        params = [{"type": "text", "text": farmer_name or "Farmer"}]
        if amount is not None:
            params.append({"type": "text", "text": f"{Decimal(amount):.2f}"})
        payload: dict = {
            "messaging_product": "whatsapp",
            "to": num,
            "type": "template",
            "template": {
                "name": settings.whatsapp_template_name,
                "language": {"code": settings.whatsapp_template_lang},
                "components": [{"type": "body", "parameters": params}],
            },
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": num,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code >= 400:
            return False, (resp.text or resp.reason_phrase)[:400]
        return True, "sent"
    except Exception as exc:  # noqa: BLE001 — surface provider errors to the cashier
        return False, str(exc)
