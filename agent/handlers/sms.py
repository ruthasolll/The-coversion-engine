from __future__ import annotations

from agent.channel_handoff import ChannelHandoffManager
from channels.email.event_emitter import HandoffEventEmitter
from channels.sms.processor import process_sms_event
from integrations.sms_client import SMSSendResult


def is_warm_lead(payload: dict) -> bool:
    lead_temperature = str(payload.get("lead_temperature", "")).strip().lower()
    email_replied = bool(payload.get("email_replied"))
    engagement_status = str(payload.get("email_engagement_status", "")).strip().lower()
    return lead_temperature in {"warm", "hot"} or email_replied or engagement_status == "replied"


def send_outbound_sms(phone: str, message: str, payload: dict | None = None) -> SMSSendResult:
    payload = payload or {}
    handoff = ChannelHandoffManager()
    return handoff.send_sms_after_email_reply(phone=phone, message=message, payload=payload)


def handle_africastalking_inbound(payload: dict) -> dict:
    return process_sms_event(payload=payload, emitter=HandoffEventEmitter())
