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
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("latency_ms", response.json())

    def test_valid_payload_emits_downstream(self) -> None:
        with patch("channels.email.webhook.handle_email_event") as mocked:
            mocked.return_value = {
                "ok": True,
                "event_type": "email_delivered",
                "email": "lead@example.org",
                "downstream": {"ok": True},
            }
            response = self.client.post(
                "/webhooks/email/resend",
                json={
                    "type": "email.delivered",
                    "created_at": "2026-04-25T10:00:00Z",
                    "data": {"to": ["lead@example.org"]},
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "success")
            self.assertEqual(response.json()["event_type"], "email_delivered")
            self.assertIn("latency_ms", response.json())

    def test_handler_failure_returns_error_outcome(self) -> None:
        with patch("channels.email.webhook.handle_email_event") as mocked:
            mocked.return_value = {"ok": False, "error": "downstream_failed"}
            response = self.client.post(
                "/webhooks/email/resend",
                json={
                    "type": "email.delivered",
                    "created_at": "2026-04-25T10:00:00Z",
                    "data": {"to": ["lead@example.org"]},
                },
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["status"], "error")
            self.assertIn("latency_ms", response.json())

    def test_hubspot_failure_is_graceful(self) -> None:
        with patch("channels.email.webhook.handle_email_event") as mocked:
            mocked.return_value = {
                "ok": False,
                "error": "hubspot_update_failed",
                "action": "record_event_only",
                "details": "VALIDATION_ERROR: Property does not exist",
                "status_code": 400,
                "body": "{\"status\":\"error\",\"message\":\"invalid property\"}",
                "payload_sent": {"email": "lead@example.org", "properties": {"email_delivery_status": "delivered"}},
                "validation": {"ok": True, "issues": []},
            }
            response = self.client.post(
                "/webhooks/email/resend",
                json={
                    "type": "email.delivered",
                    "created_at": "2026-04-25T10:00:00Z",
                    "data": {"to": ["lead@example.org"]},
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")
            self.assertEqual(response.json()["action"], "record_event_only")
            self.assertEqual(response.json()["hubspot_status"], "failed")
            self.assertIn("details", response.json())
            self.assertEqual(response.json()["status_code"], 400)
            self.assertIn("body", response.json())
            self.assertIn("payload_sent", response.json())
            self.assertIn("validation", response.json())
            self.assertIsNone(response.json()["error"])

    def test_invalid_type_payload_returns_error(self) -> None:
        response = self.client.post(
            "/webhooks/email/resend",
            json={"type": "", "data": {"to": ["lead@example.org"]}},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")


if __name__ == "__main__":
    unittest.main()
