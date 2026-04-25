from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime, timezone

from crm.hubspot_mcp import HubSpotMCP
from integrations.sms_client import AfricasTalkingSMSClient, SMSSendResult

logger = logging.getLogger(__name__)

EMAIL_EVENT_TYPES = {"email_sent", "email_delivered", "email_bounced", "email_complained", "email_replied"}
ALLOWED_STATUSES = {"sent", "delivered", "bounced", "replied", "complained"}
ALLOWED_EMAIL_DELIVERY_STATUSES = {"sent", "delivered", "bounced", "replied"}
SAFE_HUBSPOT_FIELDS = {
    "email_delivery_status",
    "last_email_provider",
    "invalid_reason",
    "lead_status",
    "last_email_bounced_at",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _debug_hubspot_enabled() -> bool:
    return os.getenv("DEBUG_HUBSPOT", "false").strip().lower() == "true"


def _debug_print_hubspot_called() -> None:
    print("HUBSPOT FUNCTION CALLED")


def _to_iso_timestamp(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return parsed.astimezone(timezone.utc).isoformat()


def sanitize_hubspot_properties(properties: dict) -> dict:
    cleaned: dict[str, str] = {}
    for key, value in properties.items():
        if key not in SAFE_HUBSPOT_FIELDS:
            continue
        if value is None:
            continue
        if not isinstance(value, (str, int, float, bool)):
            continue
        text = str(value).strip()
        if not text:
            continue

        if key == "email_delivery_status":
            normalized = text.lower()
            if normalized not in ALLOWED_EMAIL_DELIVERY_STATUSES:
                normalized = "sent"
            cleaned[key] = normalized
            continue

        if key.endswith("_at"):
            iso = _to_iso_timestamp(text)
            if not iso:
                continue
            cleaned[key] = iso
            continue

        cleaned[key] = text
    return cleaned


def sanitize_generic_properties(properties: dict) -> dict:
    cleaned: dict[str, str] = {}
    for key, value in properties.items():
        if value is None:
            continue
        if not isinstance(value, (str, int, float, bool)):
            continue
        text = str(value).strip()
        if not text:
            continue
        if key.endswith("_at"):
            iso = _to_iso_timestamp(text)
            cleaned[key] = iso if iso else text
            continue
        cleaned[key] = text
    return cleaned


def _dedupe_payloads(payloads: list[dict]) -> list[dict]:
    seen: set[tuple[tuple[str, str], ...]] = set()
    unique: list[dict] = []
    for payload in payloads:
        key = tuple(sorted((str(k), str(v)) for k, v in payload.items()))
        if key in seen:
            continue
        seen.add(key)
        unique.append(payload)
    return unique


def build_hubspot_retry_payloads(properties: dict) -> list[dict]:
    full = dict(properties)
    no_risky = {k: v for k, v in full.items() if k not in {"lead_status", "invalid_reason"}}
    core = {
        k: v
        for k, v in full.items()
        if k in {"email_delivery_status", "last_email_provider", "last_email_bounced_at"}
    }
    provider_only = {k: v for k, v in full.items() if k == "last_email_provider"}
    return _dedupe_payloads([full, no_risky, core, provider_only])


def normalize_hubspot_email_properties(event: dict) -> dict:
    event_type = str(event.get("event_type", "")).strip().lower()
    provider = str(event.get("provider", "resend")).strip().lower() or "resend"
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    raw_timestamp = str(event.get("timestamp", "")).strip()

    status = event_type.replace("email_", "").strip().lower()
    if status not in ALLOWED_STATUSES:
        status = "sent"

    lead_status_map = {
        "sent": "contacted",
        "delivered": "contacted",
        "bounced": "invalid_lead",
        "complained": "contacted",
        "replied": "replied",
    }
    properties: dict[str, str] = {
        "last_email_provider": provider,
        "lead_status": lead_status_map.get(status, "contacted"),
    }
    if status in ALLOWED_EMAIL_DELIVERY_STATUSES:
        properties["email_delivery_status"] = status

    bounce_reason = ""
    for key in ("bounce_reason", "reason", "error", "failure_reason"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            bounce_reason = value.strip()
            break
    if status == "complained":
        properties["invalid_reason"] = "complaint"
    elif status == "bounced" and bounce_reason:
        properties["invalid_reason"] = bounce_reason

    if status == "bounced":
        iso_timestamp = _to_iso_timestamp(raw_timestamp)
        if iso_timestamp:
            properties["last_email_bounced_at"] = iso_timestamp

    return sanitize_hubspot_properties(properties)


class ChannelHandoffManager:
    def __init__(self, hubspot: HubSpotMCP | None = None) -> None:
        self.hubspot = hubspot or HubSpotMCP()

    def process_event(self, event: dict) -> dict:
        channel = str(event.get("channel", "")).strip().lower()
        event_type = str(event.get("event_type", "")).strip().lower()
        entity_id = str(event.get("entity_id", "")).strip()
        provider = str(event.get("provider", "")).strip().lower()
        direction = str(event.get("direction", "inbound")).strip().lower()
        timestamp = str(event.get("timestamp", "")).strip() or _utc_now()
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}

        try:
            if channel == "email":
                return self.process_email_event(
                    {
                        "event_type": event_type,
                        "email": entity_id,
                        "provider": provider,
                        "timestamp": timestamp,
                        "payload": payload,
                    }
                )
            if channel == "sms":
                return self.process_sms_event(
                    {
                        "event_type": event_type,
                        "phone": entity_id,
                        "provider": provider,
                        "timestamp": timestamp,
                        "payload": payload,
                        "direction": direction,
                    }
                )
            if channel == "calendar":
                return self.process_calendar_event(
                    {
                        "event_type": event_type,
                        "email": entity_id,
                        "provider": provider,
                        "timestamp": timestamp,
                        "payload": payload,
                    }
                )
            if channel == "crm":
                return self.process_crm_event(
                    {
                        "event_type": event_type,
                        "entity_id": entity_id,
                        "provider": provider,
                        "timestamp": timestamp,
                        "payload": payload,
                    }
                )
            return {"ok": False, "action": "reject_event", "error": "unsupported_channel", "channel": channel}
        except Exception as exc:  # pragma: no cover - safety guard
            logger.exception("channel_handoff_process_event_failed")
            return {"ok": False, "action": "handoff_exception", "error": str(exc)}

    def determine_channel(self, payload: dict) -> tuple[str, str]:
        from agent.routing import select_channel

        return select_channel(payload)

    def process_email_event(self, event: dict) -> dict:
        event_type = str(event.get("event_type", "")).strip()
        email = str(event.get("email", "")).strip().lower()
        provider = str(event.get("provider", "")).strip().lower()
        timestamp = str(event.get("timestamp", "")).strip() or _utc_now()
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        normalized_status = str(payload.get("normalized_email_status", "")).strip().lower() or "sent"

        if event_type not in EMAIL_EVENT_TYPES:
            return {"ok": False, "action": "reject_event", "error": "unsupported_event_type", "event_type": event_type}
        if not email:
            return {"ok": False, "action": "reject_event", "error": "missing_email"}
        if not provider:
            return {"ok": False, "action": "reject_event", "error": "missing_provider"}

        normalized_event = {
            "event_type": event_type,
            "provider": provider,
            "timestamp": timestamp,
            "payload": {**payload, "normalized_email_status": normalized_status},
        }
        sanitized_properties = normalize_hubspot_email_properties(normalized_event)
        logger.info(
            "hubspot_properties_sanitized",
            extra={
                "email": email,
                "event_type": event_type,
                "properties": sanitized_properties,
            },
        )
        crm_update = self._safe_update_contact(email=email, properties=sanitized_properties)
        activity_log = self._safe_log_activity(
            email=email,
            activity_type=event_type,
            details={
                "provider": provider,
                "timestamp": timestamp,
                "payload": payload,
            },
        )

        action_map = {
            "email_sent": "record_event_only",
            "email_delivered": "record_event_only",
            "email_bounced": "mark_invalid_lead",
            "email_complained": "record_event_only",
            "email_replied": "mark_engaged_lead",
        }
        action = action_map[event_type]
        ok = bool(crm_update.get("ok", False) or crm_update.get("error") in {"hubspot_not_configured", "contact_not_found"})
        if not ok:
            action = "record_event_only"

        response = {
            "ok": ok,
            "action": action,
            "event_type": event_type,
            "email": email,
            "provider": provider,
            "timestamp": timestamp,
            "crm_update": crm_update,
            "activity_log": activity_log,
        }
        if not ok:
            response["error"] = str(crm_update.get("error", "hubspot_update_failed"))
            response["details"] = str(crm_update.get("details", ""))
            response["payload_sent"] = crm_update.get("payload_sent")
            response["validation"] = crm_update.get("validation")
            response["search_result_count"] = crm_update.get("search_result_count")
            response["status_code"] = crm_update.get("status_code")
            response["body"] = crm_update.get("body", crm_update.get("response_body"))
            if _debug_hubspot_enabled():
                response["trace"] = str(crm_update.get("trace", ""))
        else:
            response["search_result_count"] = crm_update.get("search_result_count")
            response["hubspot_action"] = crm_update.get("action")
        return response

    def process_sms_event(self, event: dict) -> dict:
        phone = str(event.get("phone", "")).strip()
        provider = str(event.get("provider", "")).strip().lower() or "africastalking"
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        direction = str(event.get("direction", "inbound")).strip().lower()
        event_type = str(event.get("event_type", "sms.inbound")).strip().lower()
        if not phone:
            return {"ok": False, "action": "reject_event", "error": "missing_phone"}

        email = str(payload.get("email", "")).strip().lower()
        activity = self._safe_log_activity(
            email=email,
            activity_type=event_type,
            details={"phone": phone, "provider": provider, "direction": direction},
        ) if email else {"ok": False, "action": "activity_skipped_missing_email"}

        return {
            "ok": True,
            "action": "sms_event_recorded",
            "event_type": event_type,
            "phone": phone,
            "provider": provider,
            "activity_log": activity,
        }

    def process_calendar_event(self, event: dict) -> dict:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        return self.process_calcom_booking(
            email=str(event.get("email", "")).strip().lower(),
            booking_id=str(payload.get("booking_id", payload.get("id", ""))).strip(),
            booking_link=str(payload.get("booking_link", payload.get("bookingUrl", payload.get("url", "")))).strip(),
            booked_at=str(payload.get("booked_at", payload.get("startTime", payload.get("start", "")))).strip(),
            notify=bool(payload.get("notify_booking_email", False)),
            provider=str(payload.get("notify_provider", "resend")).strip().lower() or "resend",
        )

    def process_crm_event(self, event: dict) -> dict:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        event_type = str(event.get("event_type", "crm.event")).strip().lower()
        return {
            "ok": True,
            "action": "crm_event_recorded",
            "event_type": event_type,
            "provider": str(event.get("provider", "hubspot")).strip().lower() or "hubspot",
            "count": int(payload.get("count", 1)),
        }

    def send_sms_after_email_reply(self, *, phone: str, message: str, payload: dict | None = None) -> SMSSendResult:
        payload = payload or {}
        if not self.email_reply_required_before_sms(payload):
            return SMSSendResult(
                ok=False,
                provider="africastalking",
                status_code=403,
                message="sms_blocked_email_reply_required",
            )
        sms_client = AfricasTalkingSMSClient()
        try:
            result = sms_client.send(phone=phone, message=message)
            logger.info(
                "sms_send_result",
                extra={
                    "phone": phone,
                    "provider": result.provider,
                    "ok": result.ok,
                    "status_code": result.status_code,
                    "dry_run": bool(getattr(result, "dry_run", False)),
                },
            )
            if result.ok and bool(getattr(result, "dry_run", False)):
                logger.info(
                    "sms_send_dry_run_success",
                    extra={
                        "phone": phone,
                        "provider": result.provider,
                        "status_code": result.status_code,
                        "message": result.message,
                    },
                )
            return result
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("sms_send_failed")
            return SMSSendResult(
                ok=False,
                provider="africastalking",
                status_code=503,
                message=f"sms_send_failed:{exc}",
            )

    def email_reply_required_before_sms(self, payload: dict) -> bool:
        replied_flag = bool(payload.get("email_replied"))
        status = str(payload.get("email_engagement_status", "")).strip().lower()
        return replied_flag or status == "replied"

    def process_enrichment_to_crm(self, *, email: str, artifact: dict) -> dict:
        if not email:
            return {"ok": False, "error": "missing_email"}

        properties = {
            "last_enrichment_at": str(artifact.get("timestamp", _utc_now())),
            "last_enrichment_confidence": str(artifact.get("overall_confidence", "")),
            "last_enrichment_summary": str(artifact.get("fusion_summary", ""))[:500],
        }
        crm_update = self._safe_update_contact(email=email, properties=properties)
        activity_log = self._safe_log_activity(
            email=email,
            activity_type="enrichment_fusion",
            details={
                "overall_confidence": artifact.get("overall_confidence"),
                "risk_score": artifact.get("risk_score"),
                "opportunity_score": artifact.get("opportunity_score"),
            },
        )
        return {"ok": bool(crm_update.get("ok")), "crm_update": crm_update, "activity_log": activity_log}

    def process_calcom_booking(
        self,
        *,
        email: str,
        booking_id: str,
        booking_link: str,
        booked_at: str,
        notify: bool = False,
        provider: str = "resend",
    ) -> dict:
        if not email:
            return {"ok": False, "error": "missing_attendee_email"}

        crm_update = self._safe_update_contact(
            email=email,
            properties={
                "calcom_booking_id": booking_id,
                "calcom_booking_link": booking_link,
                "calcom_booking_status": "booked",
                "calcom_last_booked_at": booked_at,
                "last_booking_source": "calcom",
                "tenacious_status": "draft",
            },
        )
        activity_log = self._safe_log_activity(
            email=email,
            activity_type="calendar_booking",
            details={"booking_id": booking_id, "booking_link": booking_link, "booked_at": booked_at},
        )

        notify_result = {"ok": False, "action": "notification_skipped"}
        if notify:
            notify_result = self._send_booking_notification(email=email, provider=provider, booking_link=booking_link, booked_at=booked_at)

        return {
            "ok": bool(crm_update.get("ok")),
            "action": "hubspot_updated" if crm_update.get("ok") else "hubspot_update_failed",
            "hubspot": crm_update,
            "activity_log": activity_log,
            "notification": notify_result,
        }

    def _send_booking_notification(self, *, email: str, provider: str, booking_link: str, booked_at: str) -> dict:
        from channels.email.mailersend_adapter import MailerSendAdapter
        from channels.email.resend_adapter import ResendAdapter

        subject = "Booking confirmed"
        html = f"<p>Your booking is confirmed for {booked_at}.</p><p>Link: {booking_link}</p>"
        try:
            if provider == "mailersend":
                return MailerSendAdapter().send_email(to_email=email, subject=subject, html=html)
            return ResendAdapter().send_email(to_email=email, subject=subject, html=html)
        except Exception as exc:  # pragma: no cover - network/provider defensive path
            logger.exception("booking_notification_failed")
            return {"ok": False, "error": "booking_notification_failed", "details": str(exc)}

    def _safe_update_contact(self, *, email: str, properties: dict) -> dict:
        _debug_print_hubspot_called()
        logger.info("hubspot_update_triggered", extra={"email": email, "properties": properties})
        sanitized = sanitize_hubspot_properties(properties)
        if not sanitized:
            sanitized = sanitize_generic_properties(properties)
        if not sanitized:
            logger.error(
                "hubspot_update_failed",
                extra={"email": email, "error": "sanitized_properties_empty", "properties": properties},
            )
            return {
                "ok": False,
                "error": "hubspot_update_failed",
                "details": "sanitized_properties_empty",
                "action": "record_event_only",
            }

        attempts: list[dict] = []
        try:
            retry_payloads = build_hubspot_retry_payloads(sanitized)
            for idx, retry_properties in enumerate(retry_payloads, start=1):
                logger.info(
                    "hubspot_update_attempt",
                    extra={"email": email, "attempt": idx, "properties": retry_properties},
                )
                if hasattr(self.hubspot, "update_hubspot_contact"):
                    attempt_result = self.hubspot.update_hubspot_contact(email=email, properties=retry_properties)
                else:
                    attempt_result = self.hubspot.update_contact_properties_by_email(email=email, properties=retry_properties)
                attempts.append({"attempt": idx, "properties": retry_properties, "result": attempt_result})
                if attempt_result.get("ok"):
                    attempt_result["attempt"] = idx
                    attempt_result["attempted_payloads"] = [item["properties"] for item in attempts]
                    logger.info(
                        "hubspot_update_success_after_retry",
                        extra={"email": email, "attempt": idx, "result": attempt_result},
                    )
                    return attempt_result

            primary = attempts[0]["result"] if attempts else {"ok": False, "error": "hubspot_update_failed"}
            logger.error(
                "hubspot_update_failed",
                extra={
                    "email": email,
                    "properties": sanitized,
                    "attempts": attempts,
                    "status_code": primary.get("status_code"),
                    "response_body": primary.get("body"),
                    "response": primary,
                    "error": primary.get("error", "hubspot_update_failed"),
                },
            )
            # Minimal safe fallback to isolate account-level issues.
            fallback_properties = {"email": email}
            if hasattr(self.hubspot, "update_hubspot_contact"):
                fallback = self.hubspot.update_hubspot_contact(email=email, properties=fallback_properties)
            else:
                fallback = self.hubspot.update_contact_properties_by_email(email=email, properties=fallback_properties)
            logger.info(
                "hubspot_fallback_update_response",
                extra={"email": email, "properties": fallback_properties, "response": fallback},
            )
            return {
                "ok": False,
                "error": "hubspot_update_failed",
                "details": str(primary.get("details", primary)),
                "action": "record_event_only",
                "fallback": fallback,
                "attempted_payloads": [item["properties"] for item in attempts],
                "trace": str(primary.get("trace", "")),
                "status_code": primary.get("status_code"),
                "body": primary.get("body"),
            }
        except Exception as exc:
            trace = traceback.format_exc()
            logger.exception(
                "hubspot_update_failed",
                extra={"email": email, "properties": sanitized, "error": str(exc), "trace": trace},
            )
            return {
                "ok": False,
                "error": "hubspot_update_failed",
                "details": str(exc),
                "trace": trace,
                "action": "record_event_only",
            }

    def _safe_log_activity(self, *, email: str, activity_type: str, details: dict) -> dict:
        try:
            return self.hubspot.record_activity_by_email(email=email, activity_type=activity_type, details=details)
        except Exception as exc:
            logger.exception("hubspot_activity_log_failed", extra={"email": email, "activity_type": activity_type})
            return {"ok": False, "error": "hubspot_activity_log_exception", "details": str(exc)}
