from __future__ import annotations

from fastapi import APIRouter, Request

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

    hubspot = hubspot or HubSpotMCP()
    update_result = hubspot.update_contact_properties_by_email(
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
    return {
        "ok": bool(update_result.get("ok")),
        "action": "hubspot_updated" if update_result.get("ok") else "hubspot_update_failed",
        "event": trigger,
        "hubspot": update_result,
    }


@router.post("/calcom")
async def calcom_webhook(request: Request) -> dict:
    payload = await request.json()
    result = process_calcom_booking_event(payload)
    return {"received": True, "provider": "calcom", "result": result}
