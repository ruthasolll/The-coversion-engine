from __future__ import annotations

import os
from typing import Any

import requests


class CalComClient:
    base_url = "https://api.cal.com/v2"

    def list_event_types(self) -> dict:
        api_key = os.getenv("CALCOM_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "missing_calcom_api_key"}

        response = requests.get(
            f"{self.base_url}/event-types",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        return {"ok": response.ok, "status_code": response.status_code, "body": response.text}

    def create_booking(
        self,
        event_type_id: str,
        start: str,
        attendee_name: str,
        attendee_email: str,
        timezone: str = "Africa/Nairobi",
    ) -> dict:
        api_key = os.getenv("CALCOM_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "missing_calcom_api_key"}

        if not event_type_id:
            return {"ok": False, "error": "missing_event_type_id"}
        if not start or not attendee_email:
            return {"ok": False, "error": "missing_booking_fields"}

        payload = {
            "eventTypeId": event_type_id,
            "start": start,
            "responses": {
                "name": attendee_name,
                "email": attendee_email,
            },
            "timeZone": timezone,
        }
        try:
            response = requests.post(
                f"{self.base_url}/bookings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=20,
            )
        except requests.RequestException as exc:
            return {"ok": False, "status_code": 503, "error": f"calcom_request_failed:{exc}"}

        body: Any
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}
        booking_id = ""
        if isinstance(body, dict):
            booking_id = str(body.get("id", body.get("bookingId", "")))
        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "booking_id": booking_id,
            "body": body,
        }
