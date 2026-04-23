from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhooks/calendar", tags=["calendar-webhooks"])


@router.post("/calcom")
async def calcom_webhook(request: Request) -> dict:
    payload = await request.json()
    trigger = payload.get("triggerEvent") or payload.get("event")
    return {"received": True, "provider": "calcom", "event": trigger}
