from __future__ import annotations

from dataclasses import dataclass

from agent.channel_handoff import ChannelHandoffManager
from agent.policies.stop_unsub import STOP_WORDS
from integrations.sms_client import SMSSendResult


@dataclass
class DownstreamSMSEvent:
    event_type: str
    phone: str
    provider: str
    text: str
    payload: dict


class SMSDownstream:
    def handle(self, event: DownstreamSMSEvent) -> dict:
        return {
            "accepted": True,
            "event_type": event.event_type,
            "phone": event.phone,
            "provider": event.provider,
        }


def is_warm_lead(payload: dict) -> bool:
    email_replied = bool(payload.get("email_replied"))
    engagement_status = str(payload.get("email_engagement_status", "")).strip().lower()
    return email_replied or engagement_status == "replied"


def send_outbound_sms(phone: str, message: str, payload: dict | None = None) -> SMSSendResult:
    payload = payload or {}
    handoff = ChannelHandoffManager()
    return handoff.send_sms_after_email_reply(phone=phone, message=message, payload=payload)


def handle_africastalking_inbound(payload: dict, downstream: SMSDownstream | None = None) -> dict:
    downstream = downstream or SMSDownstream()

    from_phone = str(payload.get("from", payload.get("phoneNumber", ""))).strip()
    text = str(payload.get("text", payload.get("message", ""))).strip()
    if not from_phone:
        return {"ok": False, "error": "missing_from"}
    if not text:
        return {"ok": False, "error": "missing_text"}

    inbound_text = text.lower()
    event_type = "sms.inbound"
    if inbound_text in STOP_WORDS:
        event_type = "sms.stop_or_unsubscribe"

    routed = downstream.handle(
        DownstreamSMSEvent(
            event_type=event_type,
            phone=from_phone,
            provider="africastalking",
            text=text,
            payload=payload,
        )
    )
    return {"ok": True, "action": "forwarded", "downstream": routed}
