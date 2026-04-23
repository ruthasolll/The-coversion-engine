from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhooks/sms", tags=["sms-webhooks"])


@router.post("/africastalking")
async def africastalking_webhook(request: Request) -> dict:
    form = await request.form()
    return {
        "received": True,
        "provider": "africastalking",
        "from": form.get("from"),
        "text": form.get("text"),
    }
