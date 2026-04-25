from __future__ import annotations

import logging
import os

import requests

from channels.email.event_emitter import EmailEventEmitter, HandoffEmailEventEmitter, build_email_event

logger = logging.getLogger(__name__)

RESEND_FREE_TIER_FROM = "onboarding@resend.dev"
RESEND_FREE_TIER_TO = "ruthsoll87@gmail.com"


class ResendAdapter:
    base_url = "https://api.resend.com"

    def send_email(self, to_email: str, subject: str, html: str, emitter: EmailEventEmitter | None = None) -> dict:
        api_key = os.getenv("RESEND_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "missing_resend_config"}
        if "@" not in to_email:
            return {"ok": False, "error": "invalid_email", "provider": "resend"}

        # Resend free-tier constraint:
        # "from" must be onboarding@resend.dev and "to" must be the signup email.
        from_email = RESEND_FREE_TIER_FROM
        actual_to_email = RESEND_FREE_TIER_TO
        intended_to_email = to_email.strip().lower()
        logger.info(
            "resend_free_tier_routing",
            extra={
                "intended_to": intended_to_email,
                "actual_to": actual_to_email,
                "from": from_email,
            },
        )

        try:
            response = requests.post(
                f"{self.base_url}/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"from": from_email, "to": [actual_to_email], "subject": subject, "html": html},
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
                email=intended_to_email,
                provider="resend",
                payload={
                    "status_code": response.status_code,
                    "body": response.text,
                    "actual_to": actual_to_email,
                    "from": from_email,
                },
            )
        )
        return {
            "ok": True,
            "provider": "resend",
            "status_code": response.status_code,
            "body": response.text,
            "event": "email_sent",
            "intended_to": intended_to_email,
            "actual_to": actual_to_email,
            "from": from_email,
            "downstream": event_result,
        }
