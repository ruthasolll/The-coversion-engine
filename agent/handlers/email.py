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


def _is_hubspot_validation_error(error_value: object) -> bool:
    text = str(error_value or "").upper()
    return "VALIDATION_ERROR" in text or "PROPERTY" in text


def _attempt_hubspot_update(hubspot: HubSpotMCP, email: str, properties: dict) -> dict:
    try:
        return hubspot.update_contact_properties_by_email(email=email, properties=properties)
    except Exception as exc:
        logger.exception("hubspot_update_failed", extra={"email": email})
        return {"ok": False, "error": "hubspot_exception", "details": str(exc)}


def handle_email_event(event: dict, hubspot: HubSpotMCP | None = None) -> dict:
    start_time = time.time()
    logger.info("email_handler_event_received", extra={"event": event})
    update_result: dict = {"ok": True, "action": "no_downstream_call"}

    try:
        event_type = str(event.get("event_type", "")).strip()
        email = str(event.get("email", "")).strip().lower()
        timestamp = str(event.get("timestamp", "")).strip() or _utc_now()
        provider = str(event.get("provider", "")).strip().lower()

        if event_type not in SUPPORTED_EVENTS:
            logger.warning("email_handler_unsupported_event_type", extra={"event_type": event_type})
            return {"ok": False, "action": "reject_event", "error": "unsupported_event_type", "event_type": event_type}
        if not email:
            logger.warning("email_handler_missing_email", extra={"event_type": event_type})
            return {"ok": False, "action": "reject_event", "error": "missing_email"}
        if not provider:
            logger.warning("email_handler_missing_provider", extra={"event_type": event_type, "email": email})
            return {"ok": False, "action": "reject_event", "error": "missing_provider"}

        downstream_event = DownstreamEmailEvent(
            event_type=event_type,
            email=email,
            timestamp=timestamp,
            provider=provider,
            payload=event.get("payload", {}) if isinstance(event.get("payload"), dict) else {},
        )
        logger.info("email_handler_event_normalized", extra={"event": downstream_event.__dict__})

        # Business logic by event type.
        if downstream_event.event_type in {"email_sent", "email_delivered"}:
            action = "record_event_only"
            logger.info(
                "email_handler_decision_log_only",
                extra={"event_type": downstream_event.event_type, "email": downstream_event.email},
            )
            result_ok = True
        else:
            hubspot = hubspot or HubSpotMCP()
            properties = _event_properties(downstream_event)
            if downstream_event.event_type == "email_bounced":
                properties.update(
                    {
                        "lead_status": "invalid_lead",
                        "invalid_reason": "email_bounced",
                    }
                )
                action = "mark_invalid_lead"
            else:
                properties.update(
                    {
                        "lead_status": "engaged",
                        "last_engagement_channel": "email",
                    }
                )
                action = "mark_engaged_lead"

            logger.info(
                "email_handler_decision_update_hubspot",
                extra={
                    "event_type": downstream_event.event_type,
                    "email": downstream_event.email,
                    "action": action,
                    "properties": properties,
                },
            )
            update_result = _attempt_hubspot_update(
                hubspot=hubspot,
                email=downstream_event.email,
                properties=properties,
            )

            result_ok = bool(update_result.get("ok"))
            if result_ok:
                logger.info(
                    "email_handler_downstream_succeeded",
                    extra={"email": downstream_event.email, "event_type": downstream_event.event_type, "action": action},
                )
            else:
                error_code = str(update_result.get("error", "unknown_error"))
                logger.warning(
                    "email_handler_downstream_failed",
                    extra={
                        "email": downstream_event.email,
                        "event_type": downstream_event.event_type,
                        "action": action,
                        "error": error_code,
                    },
                )
                # HubSpot should never make webhook processing fail; degrade gracefully.
                if error_code in {"hubspot_not_configured", "contact_not_found", "hubspot_exception"} or _is_hubspot_validation_error(
                    update_result.get("details", error_code)
                ):
                    result_ok = True
                    action = f"{action}_degraded"

        handler_latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "email_handler_latency",
            extra={"email": downstream_event.email, "event_type": downstream_event.event_type, "latency_ms": handler_latency_ms},
        )

        response = {
            "ok": result_ok,
            "action": action,
            "event_type": downstream_event.event_type,
            "email": downstream_event.email,
            "provider": downstream_event.provider,
            "timestamp": downstream_event.timestamp,
            "latency_ms": handler_latency_ms,
        }
        if update_result and update_result.get("action") != "no_downstream_call":
            response["downstream"] = update_result
        if not result_ok and "error" in update_result:
            response["error"] = str(update_result.get("error"))
        if result_ok and not update_result.get("ok") and "error" in update_result:
            response["warning"] = str(update_result.get("error"))
        return response
    except Exception as exc:
        logger.exception("email_handler_unexpected_failure")
        return {
            "ok": False,
            "action": "handler_failure",
            "error": "unexpected_handler_exception",
            "details": str(exc),
        }
