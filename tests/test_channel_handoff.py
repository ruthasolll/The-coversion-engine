from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.channel_handoff import ChannelHandoffManager, normalize_hubspot_email_properties, sanitize_hubspot_properties


class FakeHubSpot:
    def __init__(self) -> None:
        self.updates: list[dict] = []
        self.activities: list[dict] = []

    def update_contact_properties_by_email(self, email: str, properties: dict) -> dict:
        self.updates.append({"email": email, "properties": properties})
        return {"ok": True, "email": email, "contact_id": "c-1"}

    def update_hubspot_contact(self, email: str, properties: dict) -> dict:
        return self.update_contact_properties_by_email(email=email, properties=properties)

    def record_activity_by_email(self, email: str, activity_type: str, details: dict) -> dict:
        self.activities.append({"email": email, "activity_type": activity_type, "details": details})
        return {"ok": True, "activity_type": activity_type}


class FailingHubSpot:
    def update_contact_properties_by_email(self, email: str, properties: dict) -> dict:
        return {"ok": False, "error": "hubspot_update_failed", "details": "VALIDATION_ERROR bad property"}

    def update_hubspot_contact(self, email: str, properties: dict) -> dict:
        return self.update_contact_properties_by_email(email=email, properties=properties)

    def record_activity_by_email(self, email: str, activity_type: str, details: dict) -> dict:
        return {"ok": True, "activity_type": activity_type}


class ChannelHandoffTests(unittest.TestCase):
    def test_normalize_hubspot_email_properties_output_shape(self) -> None:
        normalized = normalize_hubspot_email_properties(
            {
                "event_type": "email_bounced",
                "provider": "resend",
                "timestamp": "2026-04-25T10:00:00Z",
                "payload": {"reason": "mailbox full"},
            }
        )
        self.assertEqual(normalized["email_delivery_status"], "bounced")
        self.assertEqual(normalized["last_email_provider"], "resend")
        self.assertEqual(normalized["invalid_reason"], "mailbox full")
        self.assertIn("last_email_bounced_at", normalized)
        self.assertNotIn("unknown_field", normalized)

    def test_sanitize_hubspot_properties_filters_and_normalizes(self) -> None:
        cleaned = sanitize_hubspot_properties(
            {
                "email_delivery_status": "EMAIL_DELIVERED",
                "last_email_provider": "resend",
                "last_email_bounced_at": "2026-04-25T10:00:00Z",
                "unknown_field": "x",
                "invalid_reason": "",
                "lead_status": None,
            }
        )
        self.assertEqual(cleaned["email_delivery_status"], "sent")
        self.assertEqual(cleaned["last_email_provider"], "resend")
        self.assertIn("last_email_bounced_at", cleaned)
        self.assertNotIn("unknown_field", cleaned)
        self.assertNotIn("invalid_reason", cleaned)

    def test_email_replied_event_updates_crm_and_activity(self) -> None:
        hubspot = FakeHubSpot()
        manager = ChannelHandoffManager(hubspot=hubspot)  # type: ignore[arg-type]
        result = manager.process_email_event(
            {
                "event_type": "email_replied",
                "email": "lead@example.org",
                "provider": "resend",
                "timestamp": "2026-04-25T10:00:00Z",
                "payload": {},
            }
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "mark_engaged_lead")
        self.assertEqual(hubspot.activities[0]["activity_type"], "email_replied")
        self.assertEqual(hubspot.updates[0]["properties"]["lead_status"], "replied")

    def test_email_complained_sets_invalid_reason(self) -> None:
        hubspot = FakeHubSpot()
        manager = ChannelHandoffManager(hubspot=hubspot)  # type: ignore[arg-type]
        result = manager.process_email_event(
            {
                "event_type": "email_complained",
                "email": "lead@example.org",
                "provider": "resend",
                "timestamp": "2026-04-25T10:00:00Z",
                "payload": {},
            }
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "record_event_only")
        self.assertEqual(hubspot.updates[0]["properties"]["invalid_reason"], "complaint")

    @patch("agent.channel_handoff.os.getenv")
    def test_hubspot_failure_returns_details_and_record_only_action(self, mocked_getenv) -> None:
        mocked_getenv.side_effect = lambda key, default="": "true" if key == "DEBUG_HUBSPOT" else default
        manager = ChannelHandoffManager(hubspot=FailingHubSpot())  # type: ignore[arg-type]
        result = manager.process_email_event(
            {
                "event_type": "email_bounced",
                "email": "lead@example.org",
                "provider": "resend",
                "timestamp": "2026-04-25T10:00:00Z",
                "payload": {"normalized_email_status": "bounced"},
            }
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["action"], "record_event_only")
        self.assertEqual(result["error"], "hubspot_update_failed")
        self.assertIn("details", result)

    def test_sms_transition_requires_email_reply(self) -> None:
        manager = ChannelHandoffManager(hubspot=FakeHubSpot())  # type: ignore[arg-type]
        self.assertFalse(manager.email_reply_required_before_sms({"email_replied": False}))
        self.assertTrue(manager.email_reply_required_before_sms({"email_replied": True}))


if __name__ == "__main__":
    unittest.main()
