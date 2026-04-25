from __future__ import annotations

import logging
import time

from agent.channel_handoff import ChannelHandoffManager
from channels.email.event_emitter import HandoffEmailEventEmitter
from channels.email.processor import process_email_event

logger = logging.getLogger(__name__)

ALLOWED_STATUSES = {"sent", "delivered", "bounced", "replied", "complained"}


def normalize_email_status(event_type: str) -> str:
    raw = (event_type or "").strip().lower()
    if raw.startswith("email_"):
        raw = raw[len("email_") :]
    if raw in ALLOWED_STATUSES:
        return raw
    return "sent"


def handle_email_event(event: dict, handoff: ChannelHandoffManager | None = None) -> dict:
    start_time = time.time()
    logger.info("email_handler_event_received", extra={"event": event})
    logger.info(
        "email_pipeline_stage",
        extra={
            "stage": "handler_entry",
            "event_type": event.get("event_type"),
            "email": event.get("email"),
        },
    )
    handoff = handoff or ChannelHandoffManager()

    try:
        raw_event_type = str(event.get("event_type", "")).strip()
        status = normalize_email_status(raw_event_type)
        logger.info("normalized_email_status=%s raw_event=%s", status, raw_event_type)

        normalized_event_type = raw_event_type if raw_event_type else f"email_{status}"
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        payload["normalized_email_status"] = status

        safe_event = {
            **event,
            "event_type": normalized_event_type,
            "payload": payload,
        }

        result = process_email_event(
            event=safe_event,
            emitter=HandoffEmailEventEmitter(handoff=handoff),
        )
        latency_ms = round((time.time() - start_time) * 1000, 2)
        result["latency_ms"] = latency_ms
        logger.info(
            "email_handler_event_completed",
            extra={
                "event_type": event.get("event_type"),
                "email": event.get("email"),
                "ok": bool(result.get("ok")),
                "latency_ms": latency_ms,
            },
        )
        return result
    except Exception as exc:
        logger.exception("email_handler_unexpected_failure")
        return {
            "ok": False,
            "action": "handler_failure",
            "error": "unexpected_handler_exception",
            "details": str(exc),
            "latency_ms": round((time.time() - start_time) * 1000, 2),
        }
