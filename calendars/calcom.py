from __future__ import annotations

import os

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
