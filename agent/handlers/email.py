from __future__ import annotations

import logging
import time

from agent.channel_handoff import ChannelHandoffManager
from channels.email.event_emitter import HandoffEmailEventEmitter
from channels.email.processor import process_email_event

logger = logging.getLogger(__name__)


def handle_email_event(event: dict, handoff: ChannelHandoffManager | None = None) -> dict:
    start_time = time.time()
    logger.info("email_handler_event_received", extra={"event": event})
    handoff = handoff or ChannelHandoffManager()

    try:
        result = process_email_event(
            event=event,
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
