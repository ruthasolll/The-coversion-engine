from __future__ import annotations

import logging
import os

import requests

from channels.email.event_emitter import EmailEventEmitter, HandoffEmailEventEmitter, build_email_event

logger = logging.getLogger(__name__)


class MailerSendAdapter:
    base_url = "https://api.mailersend.com/v1"

    def send_email(self, to_email: str, subject: str, html: str, emitter: EmailEventEmitter | None = None) -> dict:
        api_key = os.getenv("MAILERSEND_API_KEY", "")
        from_email = os.getenv("MAILERSEND_FROM_EMAIL", "")
        reply_to = os.getenv("MAILERSEND_REPLY_TO", from_email)
        if not api_key or not from_email:
            return {"ok": False, "error": "missing_mailersend_config"}
        if "@" not in to_email:
            return {"ok": False, "error": "invalid_email", "provider": "mailersend"}

        payload = {
            "from": {"email": from_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "html": html,
            "reply_to": [{"email": reply_to}],
        }

        try:
            response = requests.post(
                f"{self.base_url}/email",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=15,
            )
        except requests.Timeout:
            logger.exception("mailersend_timeout")
            return {"ok": False, "error": "provider_timeout", "provider": "mailersend"}
        except requests.RequestException as exc:
            logger.exception("mailersend_api_failure")
            return {"ok": False, "error": "api_failure", "provider": "mailersend", "details": str(exc)}

        if not response.ok:
            logger.error("mailersend_send_failed status_code=%s body=%s", response.status_code, response.text)
            return {
                "ok": False,
                "error": "send_failed",
                "provider": "mailersend",
                "status_code": response.status_code,
                "body": response.text,
            }

        emitter = emitter or HandoffEmailEventEmitter()
        downstream = emitter.emit(
            build_email_event(
                event_type="email_sent",
                email=to_email.strip().lower(),
                provider="mailersend",
                payload={"status_code": response.status_code, "body": response.text},
            )
        )
        return {
            "ok": True,
            "provider": "mailersend",
            "status_code": response.status_code,
            "body": response.text,
            "event": "email_sent",
            "downstream": downstream,
        }
