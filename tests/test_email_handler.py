from __future__ import annotations

import unittest

from agent.handlers.email import handle_email_event
from channels.email.webhook import _normalize_resend


class FakeHandoff:
    def __init__(self, ok: bool = True, error: str = "") -> None:
        self.ok = ok
        self.error = error
        self.calls: list[dict] = []

    def process_email_event(self, event: dict) -> dict:
        self.calls.append(event)
        if self.ok:
            return {"ok": True, "action": "record_event_only", "event_type": event.get("event_type")}
        return {"ok": False, "action": "reject_event", "error": self.error or "failed"}


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

    def test_normalize_resend_complaint_maps_to_bounce(self) -> None:
        event = _normalize_resend(
            {
                "type": "email.complained",
                "created_at": "2026-04-25T10:00:00Z",
                "data": {"to": ["lead@example.org"]},
            }
        )
        self.assertEqual(event["event_type"], "email_bounced")

    def test_handle_email_event_uses_handoff(self) -> None:
        handoff = FakeHandoff(ok=True)
        result = handle_email_event(
            {
                "event_type": "email_delivered",
                "email": "lead@example.org",
                "timestamp": "2026-04-25T10:00:00Z",
                "provider": "resend",
                "payload": {"id": "evt-1"},
            },
            handoff=handoff,  # type: ignore[arg-type]
        )
        self.assertTrue(result["ok"])
        self.assertEqual(handoff.calls[0]["event_type"], "email_delivered")
        self.assertIn("latency_ms", result)

    def test_handoff_failure_is_returned(self) -> None:
        handoff = FakeHandoff(ok=False, error="unsupported_event_type")
        result = handle_email_event(
            {
                "event_type": "email_unknown",
                "email": "lead@example.org",
                "provider": "resend",
            },
            handoff=handoff,  # type: ignore[arg-type]
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "unsupported_event_type")


if __name__ == "__main__":
    unittest.main()
