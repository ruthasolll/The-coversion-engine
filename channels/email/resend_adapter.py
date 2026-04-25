from __future__ import annotations

import logging
import os

import requests

from channels.email.event_emitter import EmailEventEmitter, HandoffEmailEventEmitter, build_email_event

logger = logging.getLogger(__name__)


class ResendAdapter:
    base_url = "https://api.resend.com"

    def send_email(self, to_email: str, subject: str, html: str, emitter: EmailEventEmitter | None = None) -> dict:
        api_key = os.getenv("RESEND_API_KEY", "")
        from_email = os.getenv("RESEND_FROM_EMAIL", "")
        if not api_key or not from_email:
            return {"ok": False, "error": "missing_resend_config"}
        if "@" not in to_email:
            return {"ok": False, "error": "invalid_email", "provider": "resend"}

        try:
            response = requests.post(
                f"{self.base_url}/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"from": from_email, "to": [to_email], "subject": subject, "html": html},
                timeout=15,
            )
        except requests.Timeout:
            logger.exception("resend_timeout")
            return {"ok": False, "error": "provider_timeout", "provider": "resend"}
        except requests.RequestException as exc:
            logger.exception("resend_api_failure")
            return {"ok": False, "error": "api_failure", "provider": "resend", "details": str(exc)}

        if not response.ok:
            logger.error("resend_send_failed status_code=%s body=%s", response.status_code, response.text)
            return {
                "ok": False,
                "error": "send_failed",
                "provider": "resend",
                "status_code": response.status_code,
                "body": response.text,
            }
        emitter = emitter or HandoffEmailEventEmitter()
        event_result = emitter.emit(
            build_email_event(
                event_type="email_sent",
                email=to_email.strip().lower(),
                provider="resend",
                payload={"status_code": response.status_code, "body": response.text},
            )
        )
        return {
            "ok": True,
            "provider": "resend",
            "status_code": response.status_code,
            "body": response.text,
            "event": "email_sent",
            "downstream": event_result,
        }
