from __future__ import annotations

import logging
from datetime import datetime, timezone

from crm.hubspot_mcp import HubSpotMCP
from integrations.sms_client import AfricasTalkingSMSClient, SMSSendResult

logger = logging.getLogger(__name__)

EMAIL_EVENT_TYPES = {"email_sent", "email_delivered", "email_bounced", "email_replied"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChannelHandoffManager:
    def __init__(self, hubspot: HubSpotMCP | None = None) -> None:
        self.hubspot = hubspot or HubSpotMCP()

    def process_email_event(self, event: dict) -> dict:
        event_type = str(event.get("event_type", "")).strip()
        email = str(event.get("email", "")).strip().lower()
        provider = str(event.get("provider", "")).strip().lower()
        timestamp = str(event.get("timestamp", "")).strip() or _utc_now()
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}

        if event_type not in EMAIL_EVENT_TYPES:
            return {"ok": False, "action": "reject_event", "error": "unsupported_event_type", "event_type": event_type}
        if not email:
            return {"ok": False, "action": "reject_event", "error": "missing_email"}
        if not provider:
            return {"ok": False, "action": "reject_event", "error": "missing_provider"}

        properties = self._email_properties(event_type=event_type, provider=provider, timestamp=timestamp)
        crm_update = self._safe_update_contact(email=email, properties=properties)
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
            "email_replied": "mark_engaged_lead",
        }
        action = action_map[event_type]
        ok = bool(crm_update.get("ok", False) or crm_update.get("error") in {"hubspot_not_configured", "contact_not_found"})
        if not ok:
            action = f"{action}_degraded"

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
            response["error"] = str(crm_update.get("error", "crm_update_failed"))
        return response

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
        return sms_client.send(phone=phone, message=message)

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
        try:
            return self.hubspot.update_contact_properties_by_email(email=email, properties=properties)
        except Exception as exc:
            logger.exception("hubspot_update_failed", extra={"email": email})
            return {"ok": False, "error": "hubspot_exception", "details": str(exc)}

    def _safe_log_activity(self, *, email: str, activity_type: str, details: dict) -> dict:
        try:
            return self.hubspot.record_activity_by_email(email=email, activity_type=activity_type, details=details)
        except Exception as exc:
            logger.exception("hubspot_activity_log_failed", extra={"email": email, "activity_type": activity_type})
            return {"ok": False, "error": "hubspot_activity_log_exception", "details": str(exc)}

    def _email_properties(self, *, event_type: str, provider: str, timestamp: str) -> dict:
        base = {"last_email_provider": provider}
        if event_type == "email_sent":
            base["last_email_sent_at"] = timestamp
            return base
        if event_type == "email_delivered":
            base["last_email_delivered_at"] = timestamp
            return base
        if event_type == "email_bounced":
            base.update(
                {
                    "last_email_bounced_at": timestamp,
                    "email_delivery_status": "bounced",
                    "lead_status": "invalid_lead",
                    "invalid_reason": "email_bounced",
                }
            )
            return base
        if event_type == "email_replied":
            base.update(
                {
                    "last_email_reply_at": timestamp,
                    "email_engagement_status": "replied",
                    "lead_status": "engaged",
                    "last_engagement_channel": "email",
                }
            )
            return base
        return base
