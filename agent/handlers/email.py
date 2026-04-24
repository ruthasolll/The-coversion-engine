from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from crm.hubspot_mcp import HubSpotMCP

logger = logging.getLogger(__name__)

SUPPORTED_EVENTS = {
    "email_sent",
    "email_delivered",
    "email_bounced",
    "email_replied",
}


@dataclass
class DownstreamEmailEvent:
    event_type: str
    email: str
    timestamp: str
    provider: str
    payload: dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_properties(event: DownstreamEmailEvent) -> dict:
    if event.event_type == "email_sent":
        return {
            "last_email_sent_at": event.timestamp,
            "last_email_provider": event.provider,
        }
    if event.event_type == "email_delivered":
        return {
            "last_email_delivered_at": event.timestamp,
            "last_email_provider": event.provider,
        }
    if event.event_type == "email_bounced":
        return {
            "last_email_bounced_at": event.timestamp,
            "email_delivery_status": "bounced",
            "last_email_provider": event.provider,
        }
    if event.event_type == "email_replied":
        return {
            "last_email_reply_at": event.timestamp,
            "email_engagement_status": "replied",
            "last_email_provider": event.provider,
        }
    return {"last_email_provider": event.provider}


def handle_email_event(event: dict, hubspot: HubSpotMCP | None = None) -> dict:
    start_time = time.time()
    logger.info("email_handler_event_received", extra={"event": event})

    event_type = str(event.get("event_type", "")).strip()
    email = str(event.get("email", "")).strip().lower()
    timestamp = str(event.get("timestamp", "")).strip() or _utc_now()
    provider = str(event.get("provider", "")).strip().lower()

    if event_type not in SUPPORTED_EVENTS:
        logger.warning("email_handler_unsupported_event_type", extra={"event_type": event_type})
        return {"ok": False, "error": "unsupported_event_type", "event_type": event_type}
    if not email:
        logger.warning("email_handler_missing_email", extra={"event_type": event_type})
        return {"ok": False, "error": "missing_email"}
    if not provider:
        logger.warning("email_handler_missing_provider", extra={"event_type": event_type, "email": email})
        return {"ok": False, "error": "missing_provider"}

    downstream_event = DownstreamEmailEvent(
        event_type=event_type,
        email=email,
        timestamp=timestamp,
        provider=provider,
        payload=event.get("payload", {}) if isinstance(event.get("payload"), dict) else {},
    )

    logger.info("email_handler_event_normalized", extra={"event": downstream_event.__dict__})

    hubspot = hubspot or HubSpotMCP()
    properties = _event_properties(downstream_event)
    logger.info(
        "email_handler_decision_update_hubspot",
        extra={"event_type": downstream_event.event_type, "email": downstream_event.email, "properties": properties},
    )
    try:
        update_result = hubspot.update_contact_properties_by_email(
            email=downstream_event.email,
            properties=properties,
        )
    except Exception as exc:
        logger.exception("email_handler_downstream_exception")
        return {"ok": False, "error": "downstream_exception", "details": str(exc)}
    downstream_ok = bool(update_result.get("ok"))
    if update_result.get("error") == "hubspot_not_configured":
        logger.warning("hubspot_not_configured_email_event email=%s", downstream_event.email)
        downstream_ok = True
    elif not downstream_ok:
        logger.warning(
            "email_handler_downstream_failed",
            extra={"email": downstream_event.email, "event_type": downstream_event.event_type, "result": update_result},
        )
    else:
        logger.info(
            "email_handler_downstream_succeeded",
            extra={"email": downstream_event.email, "event_type": downstream_event.event_type},
        )

    handler_latency_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        "email_handler_latency",
        extra={"email": downstream_event.email, "event_type": downstream_event.event_type, "latency_ms": handler_latency_ms},
    )

    return {
        "ok": downstream_ok,
        "event_type": downstream_event.event_type,
        "email": downstream_event.email,
        "provider": downstream_event.provider,
        "timestamp": downstream_event.timestamp,
        "latency_ms": handler_latency_ms,
        "downstream": update_result,
    }
