from __future__ import annotations

import logging

from channels.email.event_emitter import EmailEventEmitter, build_email_event

logger = logging.getLogger(__name__)

SUPPORTED_EMAIL_EVENTS = {"email_sent", "email_delivered", "email_bounced", "email_replied"}


def process_email_event(event: dict, emitter: EmailEventEmitter) -> dict:
    event_type = str(event.get("event_type", "")).strip()
    email = str(event.get("email", "")).strip().lower()
    provider = str(event.get("provider", "")).strip().lower()
    timestamp = str(event.get("timestamp", "")).strip()
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}

    if event_type not in SUPPORTED_EMAIL_EVENTS:
        return {"ok": False, "error": "unsupported_event_type", "action": "reject_event"}
    if not email:
        return {"ok": False, "error": "missing_email", "action": "reject_event"}
    if not provider:
        return {"ok": False, "error": "missing_provider", "action": "reject_event"}

    emitted = emitter.emit(
        build_email_event(
            event_type=event_type,
            email=email,
            provider=provider,
            timestamp=timestamp or None,
            payload=payload,
        )
    )
    logger.info(
        "email_event_processed",
        extra={
            "event_type": event_type,
            "email": email,
            "provider": provider,
            "ok": bool(emitted.get("ok")),
        },
    )
    return emitted
