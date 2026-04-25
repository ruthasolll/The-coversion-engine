from __future__ import annotations

from fastapi import APIRouter, Header, Request
from channels.sms.webhook import process_africastalking_webhook

router = APIRouter(prefix="/api/routes/sms_webhook", tags=["sms-webhook"])


@router.post("/africastalking")
async def africastalking_webhook(
    request: Request,
    x_africastalking_signature: str | None = Header(default=None),
) -> dict:
    return await process_africastalking_webhook(
        request,
        x_africastalking_signature=x_africastalking_signature,
    )
