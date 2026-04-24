from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)


class MailerSendAdapter:
    base_url = "https://api.mailersend.com/v1"

    def send_email(self, to_email: str, subject: str, html: str) -> dict:
        api_key = os.getenv("MAILERSEND_API_KEY", "")
        from_email = os.getenv("MAILERSEND_FROM_EMAIL", "")
        if not api_key or not from_email:
            return {"ok": False, "error": "missing_mailersend_config"}
        if "@" not in to_email:
            return {"ok": False, "error": "invalid_email", "provider": "mailersend"}

        payload = {
            "from": {"email": from_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "html": html,
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
        return {"ok": True, "provider": "mailersend", "status_code": response.status_code, "body": response.text}
