from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from agent.handlers.email import handle_email_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/email", tags=["email-webhooks"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_valid_email(value: str) -> bool:
    return "@" in value and "." in value.split("@")[-1]


def _normalize_resend(payload: dict) -> dict:
    event_raw = str(payload.get("type", "")).strip().lower()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    recipients = data.get("to")
    email = ""
    if isinstance(recipients, list) and recipients:
        email = str(recipients[0]).strip().lower()
    if not email:
        email = str(data.get("email", "")).strip().lower()
    timestamp = str(data.get("created_at") or payload.get("created_at") or _utc_now())

    event_map = {
        "email.sent": "email_sent",
        "email.delivered": "email_delivered",
        "email.bounced": "email_bounced",
        "email.complained": "email_bounced",
        "email.replied": "email_replied",
    }
    event_type = event_map.get(event_raw, "")
    return {
        "event_type": event_type,
        "email": email,
        "timestamp": timestamp,
        "provider": "resend",
        "payload": payload,
    }


def _normalize_mailersend(payload: dict) -> dict:
    event_raw = str(payload.get("type", "")).strip().lower()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    email = ""
    if isinstance(data.get("email"), dict):
        email = str(data["email"].get("recipient", "")).strip().lower()
    if not email:
        email = str(data.get("recipient") or payload.get("recipient") or "").strip().lower()
    timestamp = str(data.get("created_at") or payload.get("created_at") or _utc_now())

    event_map = {
        "activity.sent": "email_sent",
        "activity.delivered": "email_delivered",
        "activity.bounced": "email_bounced",
        "activity.reply": "email_replied",
        "activity.replied": "email_replied",
    }
    event_type = event_map.get(event_raw, "")
    return {
        "event_type": event_type,
        "email": email,
        "timestamp": timestamp,
        "provider": "mailersend",
        "payload": payload,
    }


def _validate_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail={"ok": False, "error": "payload_must_be_object"})
    if "type" not in payload:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "missing_type"})


def _validate_event(event: dict) -> None:
    if not event.get("event_type"):
        raise HTTPException(status_code=400, detail={"ok": False, "error": "unsupported_event_type"})
    email = str(event.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "missing_email"})
    if not _is_valid_email(email):
        raise HTTPException(status_code=400, detail={"ok": False, "error": "invalid_email"})


@router.post("/resend")
async def resend_webhook(request: Request) -> dict:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "malformed_json"})
    except Exception as exc:
        logger.exception("resend_webhook_read_failed")
        raise HTTPException(status_code=400, detail={"ok": False, "error": f"malformed_payload:{exc}"})

    _validate_payload(payload)
    event = _normalize_resend(payload)
    _validate_event(event)
    result = handle_email_event(event)
    if not result.get("ok", False):
        raise HTTPException(status_code=400, detail=result)
    return {"received": True, "provider": "resend", "event": event, "result": result}


@router.post("/mailersend")
async def mailersend_webhook(request: Request) -> dict:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "malformed_json"})
    except Exception as exc:
        logger.exception("mailersend_webhook_read_failed")
        raise HTTPException(status_code=400, detail={"ok": False, "error": f"malformed_payload:{exc}"})

    _validate_payload(payload)
    event = _normalize_mailersend(payload)
    _validate_event(event)
    result = handle_email_event(event)
    if not result.get("ok", False):
        raise HTTPException(status_code=400, detail=result)
    return {"received": True, "provider": "mailersend", "event": event, "result": result}
