from __future__ import annotations

from fastapi import APIRouter, Header, Request

router = APIRouter(prefix="/webhooks/email", tags=["email-webhooks"])


@router.post("/resend")
async def resend_webhook(request: Request, x_resend_signature: str | None = Header(default=None)) -> dict:
    payload = await request.json()
    return {"received": True, "provider": "resend", "signature_present": bool(x_resend_signature), "event": payload.get("type")}


@router.post("/mailersend")
async def mailersend_webhook(request: Request) -> dict:
    payload = await request.json()
    return {"received": True, "provider": "mailersend", "event": payload.get("type")}
