from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from agent.main import app


class EmailWebhookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_malformed_payload_returns_400(self) -> None:
        response = self.client.post(
            "/webhooks/email/resend",
            data="not-json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)

    def test_valid_payload_emits_downstream(self) -> None:
        with patch("channels.email.webhook.handle_email_event") as mocked:
            mocked.return_value = {"ok": True, "downstream": {"ok": True}}
            response = self.client.post(
                "/webhooks/email/resend",
                json={
                    "type": "email.delivered",
                    "created_at": "2026-04-25T10:00:00Z",
                    "data": {"to": ["lead@example.org"]},
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["result"]["ok"])


if __name__ == "__main__":
    unittest.main()
