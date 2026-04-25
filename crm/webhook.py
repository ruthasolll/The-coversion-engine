from __future__ import annotations

from fastapi import APIRouter, Request

from channels.email.event_emitter import HandoffEventEmitter, build_channel_event

router = APIRouter(prefix="/webhooks/crm", tags=["crm-webhooks"])


@router.post("/hubspot")
async def hubspot_webhook(request: Request) -> dict:
    payload = await request.json()
    event_count = len(payload) if isinstance(payload, list) else 1
    emitted = HandoffEventEmitter().emit(
        build_channel_event(
            channel="crm",
            event_type="crm.hubspot_webhook",
            entity_id="hubspot",
            direction="inbound",
            provider="hubspot",
            payload={"count": event_count},
        )
    )
    return {"received": True, "provider": "hubspot", "events": event_count, "result": emitted}
