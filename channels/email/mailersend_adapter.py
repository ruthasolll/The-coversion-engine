from __future__ import annotations

import os

import requests


class MailerSendAdapter:
    base_url = "https://api.mailersend.com/v1"

    def send_email(self, to_email: str, subject: str, html: str) -> dict:
        api_key = os.getenv("MAILERSEND_API_KEY", "")
        from_email = os.getenv("MAILERSEND_FROM_EMAIL", "")
        if not api_key or not from_email:
            return {"ok": False, "error": "missing_mailersend_config"}

        payload = {
            "from": {"email": from_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "html": html,
        }
        response = requests.post(
            f"{self.base_url}/email",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        return {"ok": response.ok, "status_code": response.status_code, "body": response.text}
