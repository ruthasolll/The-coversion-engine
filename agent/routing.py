from __future__ import annotations

from agent.handlers.sms import is_warm_lead


def _sms_block_fallback(has_email: bool) -> tuple[str, str]:
    if has_email:
        return "email", "sms_blocked_not_warm_lead_fallback_email"
    return "voice", "sms_blocked_not_warm_lead"


def select_channel(payload: dict) -> tuple[str, str]:
    preferred = payload.get("preferred_channel")
    has_phone = bool(payload.get("phone"))
    has_email = bool(payload.get("email"))

    if preferred == "sms":
        if not has_phone:
            return "voice", "sms_preferred_but_no_phone"
        if not is_warm_lead(payload):
            return _sms_block_fallback(has_email=has_email)
        return "sms", "preferred_channel"

    if preferred in {"email", "voice"}:
        return preferred, "preferred_channel"

    if has_email:
        return "email", "email_available"
    if has_phone and is_warm_lead(payload):
        return "sms", "phone_only_warm_lead"
    if has_phone:
        return "voice", "sms_blocked_not_warm_lead"
    return "voice", "fallback"
