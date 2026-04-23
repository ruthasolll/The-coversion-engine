from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhooks/crm", tags=["crm-webhooks"])


@router.post("/hubspot")
async def hubspot_webhook(request: Request) -> dict:
    payload = await request.json()
    event_count = len(payload) if isinstance(payload, list) else 1
    return {"received": True, "provider": "hubspot", "events": event_count}
