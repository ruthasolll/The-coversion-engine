from __future__ import annotations

from dataclasses import dataclass

from agent.policies.stop_unsub import STOP_WORDS
from integrations.sms_client import AfricasTalkingSMSClient, SMSSendResult


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
    if bool(payload.get("warm_lead")):
        return True
    lead_temp = str(payload.get("lead_temperature", "")).strip().lower()
    return lead_temp in {"warm", "hot", "qualified"}


def send_outbound_sms(phone: str, message: str, payload: dict | None = None) -> SMSSendResult:
    payload = payload or {}
    if not is_warm_lead(payload):
        return SMSSendResult(
            ok=False,
            provider="africastalking",
            status_code=403,
            message="sms_blocked_not_warm_lead",
        )
    client = AfricasTalkingSMSClient()
    return client.send(phone=phone, message=message)


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
