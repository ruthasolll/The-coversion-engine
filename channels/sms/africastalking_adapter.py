from __future__ import annotations

import os

import requests


class AfricasTalkingAdapter:
    base_url = "https://api.africastalking.com/version1/messaging"

    def send_sms(self, phone: str, message: str) -> dict:
        username = os.getenv("AFRICASTALKING_USERNAME", "sandbox")
        api_key = os.getenv("AFRICASTALKING_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "missing_africastalking_config"}

        response = requests.post(
            self.base_url,
            headers={
                "apiKey": api_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"username": username, "to": phone, "message": message},
            timeout=15,
        )
        return {"ok": response.ok, "status_code": response.status_code, "body": response.text}
