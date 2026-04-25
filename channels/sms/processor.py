from __future__ import annotations

import logging

from channels.email.event_emitter import EmailEventEmitter, build_channel_event

logger = logging.getLogger(__name__)

SUPPORTED_SMS_EVENTS = {"sms.inbound", "sms.stop_or_unsubscribe"}


def parse_africastalking_payload(payload: dict) -> dict:
    phone = str(payload.get("from", payload.get("phoneNumber", ""))).strip()
    text = str(payload.get("text", payload.get("message", ""))).strip()
    if not phone:
        return {"ok": False, "error": "missing_from"}
    if not text:
        return {"ok": False, "error": "missing_text"}

    event_type = "sms.inbound"
    if text.lower() in {"stop", "unsubscribe", "end", "cancel", "quit"}:
        event_type = "sms.stop_or_unsubscribe"
    return {"ok": True, "event_type": event_type, "phone": phone, "text": text}


def process_sms_event(payload: dict, emitter: EmailEventEmitter) -> dict:
    parsed = parse_africastalking_payload(payload)
    if not parsed.get("ok"):
        return {"ok": False, "action": "reject_event", "error": parsed.get("error", "invalid_payload")}

    emitted = emitter.emit(
        build_channel_event(
            channel="sms",
            event_type=str(parsed["event_type"]),
            entity_id=str(parsed["phone"]),
            direction="inbound",
            provider="africastalking",
            payload={
                "text": str(parsed["text"]),
                "raw_payload": payload,
                "email": str(payload.get("email", "")).strip().lower(),
            },
        )
    )
    logger.info(
        "sms_event_processed",
        extra={"event_type": parsed["event_type"], "phone": parsed["phone"], "ok": bool(emitted.get("ok"))},
    )
    return {
        "ok": bool(emitted.get("ok")),
        "action": "forwarded",
        "event_type": parsed["event_type"],
        "phone": parsed["phone"],
        "downstream": emitted,
        "error": emitted.get("error") if not emitted.get("ok") else None,
    }
