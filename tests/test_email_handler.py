from __future__ import annotations

import unittest

from agent.handlers.email import handle_email_event
from channels.email.webhook import _normalize_resend


class FakeHubSpot:
    def __init__(self, ok: bool = True, error: str = "") -> None:
        self.ok = ok
        self.error = error
        self.calls: list[dict] = []

    def update_contact_properties_by_email(self, email: str, properties: dict) -> dict:
        self.calls.append({"email": email, "properties": properties})
        if self.ok:
            return {"ok": True, "contact_id": "c-1"}
        return {"ok": False, "error": self.error or "failed"}


class EmailHandlerTests(unittest.TestCase):
    def test_normalize_resend_bounce(self) -> None:
        event = _normalize_resend(
            {
                "type": "email.bounced",
                "created_at": "2026-04-25T10:00:00Z",
                "data": {"to": ["lead@example.org"]},
            }
        )
        self.assertEqual(event["event_type"], "email_bounced")
        self.assertEqual(event["email"], "lead@example.org")
        self.assertEqual(event["provider"], "resend")

    def test_handle_email_event_routes_to_downstream(self) -> None:
        hubspot = FakeHubSpot(ok=True)
        result = handle_email_event(
            {
                "event_type": "email_delivered",
                "email": "lead@example.org",
                "timestamp": "2026-04-25T10:00:00Z",
                "provider": "resend",
                "payload": {"id": "evt-1"},
            },
            hubspot=hubspot,  # type: ignore[arg-type]
        )
        self.assertTrue(result["ok"])
        self.assertEqual(hubspot.calls[0]["email"], "lead@example.org")
        self.assertIn("last_email_delivered_at", hubspot.calls[0]["properties"])
        self.assertIn("latency_ms", result)

    def test_missing_email_rejected(self) -> None:
        result = handle_email_event(
            {
                "event_type": "email_sent",
                "provider": "resend",
            }
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_email")


if __name__ == "__main__":
    unittest.main()
