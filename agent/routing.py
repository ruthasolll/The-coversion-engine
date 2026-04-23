from __future__ import annotations


def select_channel(payload: dict) -> tuple[str, str]:
    preferred = payload.get("preferred_channel")
    if preferred in {"email", "sms", "voice"}:
        return preferred, "preferred_channel"

    has_phone = bool(payload.get("phone"))
    has_email = bool(payload.get("email"))

    if has_email:
        return "email", "email_available"
    if has_phone:
        return "sms", "phone_only"
    return "voice", "fallback"
