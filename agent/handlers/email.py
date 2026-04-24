from __future__ import annotations

import logging
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
    event_type = str(event.get("event_type", "")).strip()
    email = str(event.get("email", "")).strip().lower()
    timestamp = str(event.get("timestamp", "")).strip() or _utc_now()
    provider = str(event.get("provider", "")).strip().lower()

    if event_type not in SUPPORTED_EVENTS:
        return {"ok": False, "error": "unsupported_event_type", "event_type": event_type}
    if not email:
        return {"ok": False, "error": "missing_email"}
    if not provider:
        return {"ok": False, "error": "missing_provider"}

    downstream_event = DownstreamEmailEvent(
        event_type=event_type,
        email=email,
        timestamp=timestamp,
        provider=provider,
        payload=event.get("payload", {}) if isinstance(event.get("payload"), dict) else {},
    )

    logger.info(
        "processing_email_event event_type=%s provider=%s email=%s",
        downstream_event.event_type,
        downstream_event.provider,
        downstream_event.email,
    )

    hubspot = hubspot or HubSpotMCP()
    update_result = hubspot.update_contact_properties_by_email(
        email=downstream_event.email,
        properties=_event_properties(downstream_event),
    )
    downstream_ok = bool(update_result.get("ok"))
    if update_result.get("error") == "hubspot_not_configured":
        logger.warning("hubspot_not_configured_email_event email=%s", downstream_event.email)
        downstream_ok = True

    return {
        "ok": downstream_ok,
        "event_type": downstream_event.event_type,
        "email": downstream_event.email,
        "provider": downstream_event.provider,
        "timestamp": downstream_event.timestamp,
        "downstream": update_result,
    }
