from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Request

from agent.handlers.sms import handle_africastalking_inbound

router = APIRouter(prefix="/webhooks/sms", tags=["sms-webhooks"])


async def process_africastalking_webhook(
    request: Request,
    *,
    x_africastalking_signature: str | None,
) -> dict:
    form = await request.form()
    payload = dict(form)

    expected_secret = os.getenv("AFRICASTALKING_WEBHOOK_SECRET", "")
    if expected_secret and not x_africastalking_signature:
        raise HTTPException(status_code=401, detail="missing_signature")

    result = handle_africastalking_inbound(payload)
    if not result.get("ok", False):
        raise HTTPException(status_code=400, detail=result.get("error", "webhook_rejected"))

    return {"received": True, "provider": "africastalking", "result": result}


@router.post("/africastalking")
async def africastalking_webhook(
    request: Request,
    x_africastalking_signature: str | None = Header(default=None),
) -> dict:
    return await process_africastalking_webhook(
        request,
        x_africastalking_signature=x_africastalking_signature,
    )
