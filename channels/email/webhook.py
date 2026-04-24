from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from agent.handlers.email import handle_email_event
from channels.email.tracing import EmailWebhookTracer

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


def _validate_payload(payload: dict) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "payload_must_be_object"
    if "type" not in payload:
        return False, "missing_type"
    return True, ""


def _validate_event(event: dict) -> tuple[bool, str]:
    if not event.get("event_type"):
        return False, "unsupported_event_type"
    email = str(event.get("email", "")).strip().lower()
    if not email:
        return False, "missing_email"
    if not _is_valid_email(email):
        return False, "invalid_email"
    return True, ""


async def _process_webhook(provider: str, request: Request, normalizer) -> JSONResponse:
    start_time = time.time()
    tracer = EmailWebhookTracer()
    raw_event_type = ""

    try:
        payload = await request.json()
        raw_event_type = str(payload.get("type", "")).strip().lower() if isinstance(payload, dict) else ""
        logger.info(
            "email_event_received",
            extra={"provider": provider, "raw_event_type": raw_event_type},
        )
        tracer.start_trace(provider=provider, raw_event_type=raw_event_type)

        valid_payload, payload_error = _validate_payload(payload)
        if not valid_payload:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            error_body = {"status": "error", "error": payload_error, "latency_ms": latency_ms}
            logger.error("email_event_payload_invalid", extra={"provider": provider, "error": payload_error})
            tracer.finalize(
                success=False,
                metadata={
                    "provider": provider,
                    "raw_event_type": raw_event_type,
                    "latency_ms": latency_ms,
                    "status": "error",
                    "error": payload_error,
                },
            )
            return JSONResponse(status_code=400, content=error_body)

        normalize_span = tracer.start_span(name="normalize_event", metadata={"provider": provider})
        normalized_event = normalizer(payload)
        tracer.end_span(normalize_span, metadata={"event_type": normalized_event.get("event_type")})
        logger.info(
            "email_event_normalized",
            extra={
                "event": {
                    "event_type": normalized_event.get("event_type"),
                    "email": normalized_event.get("email"),
                    "timestamp": normalized_event.get("timestamp"),
                    "provider": normalized_event.get("provider"),
                }
            },
        )

        valid_event, event_error = _validate_event(normalized_event)
        if not valid_event:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            error_body = {"status": "error", "error": event_error, "latency_ms": latency_ms}
            logger.error("email_event_validation_failed", extra={"provider": provider, "error": event_error})
            tracer.finalize(
                success=False,
                metadata={
                    "provider": provider,
                    "event_type": normalized_event.get("event_type"),
                    "email": normalized_event.get("email"),
                    "latency_ms": latency_ms,
                    "status": "error",
                    "error": event_error,
                },
            )
            return JSONResponse(status_code=400, content=error_body)

        logger.info(
            "email_event_handler_call",
            extra={
                "event_type": normalized_event.get("event_type"),
                "email": normalized_event.get("email"),
            },
        )
        handle_start = time.time()
        handle_span = tracer.start_span(
            name="handle_event",
            metadata={
                "event_type": normalized_event.get("event_type"),
                "email": normalized_event.get("email"),
            },
        )
        result = handle_email_event(normalized_event)
        handler_latency_ms = round((time.time() - handle_start) * 1000, 2)
        tracer.end_span(
            handle_span,
            metadata={"ok": bool(result.get("ok")), "handler_latency_ms": handler_latency_ms},
            level="ERROR" if not result.get("ok") else "DEFAULT",
        )

        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "email_event_latency",
            extra={
                "provider": provider,
                "event_type": normalized_event.get("event_type"),
                "latency_ms": latency_ms,
                "handler_latency_ms": handler_latency_ms,
            },
        )

        if not result.get("ok", False):
            logger.warning("email_event_handler_failed", extra={"provider": provider, "result": result})
            tracer.finalize(
                success=False,
                metadata={
                    "provider": provider,
                    "event_type": normalized_event.get("event_type"),
                    "email": normalized_event.get("email"),
                    "latency_ms": latency_ms,
                    "handler_latency_ms": handler_latency_ms,
                    "status": "error",
                    "error": result.get("error", "handler_failed"),
                },
            )
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error": str(result.get("error", "handler_failed")),
                    "latency_ms": latency_ms,
                },
            )

        logger.info("email_event_handler_succeeded", extra={"provider": provider, "result": result})
        tracer.finalize(
            success=True,
            metadata={
                "provider": provider,
                "event_type": normalized_event.get("event_type"),
                "email": normalized_event.get("email"),
                "latency_ms": latency_ms,
                "handler_latency_ms": handler_latency_ms,
                "status": "success",
            },
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "event_type": str(normalized_event.get("event_type", "")),
                "latency_ms": latency_ms,
            },
        )

    except json.JSONDecodeError:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.exception("email_webhook_malformed_json")
        tracer.finalize(
            success=False,
            metadata={
                "provider": provider,
                "raw_event_type": raw_event_type,
                "latency_ms": latency_ms,
                "status": "error",
                "error": "malformed_json",
            },
        )
        return JSONResponse(status_code=400, content={"status": "error", "error": "malformed_json", "latency_ms": latency_ms})
    except Exception as exc:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.exception("email_webhook_processing_failed")
        tracer.finalize(
            success=False,
            metadata={
                "provider": provider,
                "raw_event_type": raw_event_type,
                "latency_ms": latency_ms,
                "status": "error",
                "error": str(exc),
            },
        )
        return JSONResponse(status_code=500, content={"status": "error", "error": "internal_error", "latency_ms": latency_ms})


@router.post("/resend")
async def resend_webhook(request: Request) -> JSONResponse:
    return await _process_webhook("resend", request, _normalize_resend)


@router.post("/mailersend")
async def mailersend_webhook(request: Request) -> JSONResponse:
    return await _process_webhook("mailersend", request, _normalize_mailersend)
