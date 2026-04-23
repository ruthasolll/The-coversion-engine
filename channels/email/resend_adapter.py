from __future__ import annotations

import os

import requests


class ResendAdapter:
    base_url = "https://api.resend.com"

    def send_email(self, to_email: str, subject: str, html: str) -> dict:
        api_key = os.getenv("RESEND_API_KEY", "")
        from_email = os.getenv("RESEND_FROM_EMAIL", "")
        if not api_key or not from_email:
            return {"ok": False, "error": "missing_resend_config"}

        response = requests.post(
            f"{self.base_url}/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_email, "to": [to_email], "subject": subject, "html": html},
            timeout=15,
        )
        return {"ok": response.ok, "status_code": response.status_code, "body": response.text}
