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


class FakeHubSpotException:
    def update_contact_properties_by_email(self, email: str, properties: dict) -> dict:
        raise RuntimeError("400 VALIDATION_ERROR Property values were not valid")


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
        self.assertEqual(result["action"], "record_event_only")
        self.assertEqual(hubspot.calls, [])
        self.assertIn("latency_ms", result)

    def test_missing_email_rejected(self) -> None:
        result = handle_email_event(
            {
                "event_type": "email_sent",
                "provider": "resend",
            }
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["action"], "reject_event")
        self.assertEqual(result["error"], "missing_email")

    def test_bounced_marks_invalid_lead(self) -> None:
        hubspot = FakeHubSpot(ok=True)
        result = handle_email_event(
            {
                "event_type": "email_bounced",
                "email": "lead@example.org",
                "timestamp": "2026-04-25T10:00:00Z",
                "provider": "resend",
            },
            hubspot=hubspot,  # type: ignore[arg-type]
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "mark_invalid_lead")
        props = hubspot.calls[0]["properties"]
        self.assertEqual(props["lead_status"], "invalid_lead")
        self.assertEqual(props["invalid_reason"], "email_bounced")

    def test_replied_marks_engaged_lead(self) -> None:
        hubspot = FakeHubSpot(ok=True)
        result = handle_email_event(
            {
                "event_type": "email_replied",
                "email": "lead@example.org",
                "timestamp": "2026-04-25T10:00:00Z",
                "provider": "mailersend",
            },
            hubspot=hubspot,  # type: ignore[arg-type]
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "mark_engaged_lead")
        props = hubspot.calls[0]["properties"]
        self.assertEqual(props["lead_status"], "engaged")
        self.assertEqual(props["last_engagement_channel"], "email")

    def test_bounced_validation_error_is_degraded_not_failed(self) -> None:
        hubspot = FakeHubSpot(ok=False, error="VALIDATION_ERROR")
        result = handle_email_event(
            {
                "event_type": "email_bounced",
                "email": "lead@example.org",
                "timestamp": "2026-04-25T10:00:00Z",
                "provider": "resend",
            },
            hubspot=hubspot,  # type: ignore[arg-type]
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "mark_invalid_lead_degraded")
        self.assertEqual(result["warning"], "VALIDATION_ERROR")

    def test_replied_hubspot_exception_is_degraded_not_failed(self) -> None:
        result = handle_email_event(
            {
                "event_type": "email_replied",
                "email": "lead@example.org",
                "timestamp": "2026-04-25T10:00:00Z",
                "provider": "mailersend",
            },
            hubspot=FakeHubSpotException(),  # type: ignore[arg-type]
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "mark_engaged_lead_degraded")
        self.assertEqual(result["warning"], "hubspot_exception")


if __name__ == "__main__":
    unittest.main()
