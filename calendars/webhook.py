from __future__ import annotations

import os

from fastapi import APIRouter, Request

from agent.channel_handoff import ChannelHandoffManager
from crm.hubspot_mcp import HubSpotMCP

router = APIRouter(prefix="/webhooks/calendar", tags=["calendar-webhooks"])


def process_calcom_booking_event(payload: dict, hubspot: HubSpotMCP | None = None) -> dict:
    trigger = str(payload.get("triggerEvent") or payload.get("event") or "").strip()
    trigger_lc = trigger.lower()
    if trigger_lc not in {
        "booking.created",
        "booking.confirmed",
        "booking.completed",
        "booking_created",
        "booking_confirmed",
        "booking_completed",
    }:
        return {"ok": True, "action": "ignored_non_booking_event", "event": trigger}

    data = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload.get("data")
    if not isinstance(data, dict):
        data = payload

    attendee = data.get("attendee") if isinstance(data.get("attendee"), dict) else {}
    email = str(attendee.get("email") or data.get("email") or "").strip()
    booking_id = str(data.get("id") or data.get("bookingId") or "").strip()
    booking_link = str(data.get("bookingUrl") or data.get("url") or "").strip()
    booked_at = str(data.get("startTime") or data.get("start") or "").strip()
    if not email:
        return {"ok": False, "error": "missing_attendee_email", "event": trigger}

    notify_booking_email = str(payload.get("notify_booking_email", os.getenv("CALCOM_NOTIFY_BOOKING_EMAIL", "false"))).lower() == "true"
    notify_provider = str(payload.get("notify_provider", os.getenv("CALCOM_NOTIFY_PROVIDER", "resend"))).strip().lower()
    handoff = ChannelHandoffManager(hubspot=hubspot or HubSpotMCP())
    result = handoff.process_calcom_booking(
        email=email,
        booking_id=booking_id,
        booking_link=booking_link,
        booked_at=booked_at,
        notify=notify_booking_email,
        provider=notify_provider,
    )
    result["event"] = trigger
    return result


@router.post("/calcom")
async def calcom_webhook(request: Request) -> dict:
    payload = await request.json()
    result = process_calcom_booking_event(payload)
    return {"received": True, "provider": "calcom", "result": result}
