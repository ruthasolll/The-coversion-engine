from __future__ import annotations

import unittest

from agent.channel_handoff import ChannelHandoffManager


class FakeHubSpot:
    def __init__(self) -> None:
        self.updates: list[dict] = []
        self.activities: list[dict] = []

    def update_contact_properties_by_email(self, email: str, properties: dict) -> dict:
        self.updates.append({"email": email, "properties": properties})
        return {"ok": True, "email": email, "contact_id": "c-1"}

    def record_activity_by_email(self, email: str, activity_type: str, details: dict) -> dict:
        self.activities.append({"email": email, "activity_type": activity_type, "details": details})
        return {"ok": True, "activity_type": activity_type}


class ChannelHandoffTests(unittest.TestCase):
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

    def test_sms_transition_requires_email_reply(self) -> None:
        manager = ChannelHandoffManager(hubspot=FakeHubSpot())  # type: ignore[arg-type]
        self.assertFalse(manager.email_reply_required_before_sms({"email_replied": False}))
        self.assertTrue(manager.email_reply_required_before_sms({"email_replied": True}))


if __name__ == "__main__":
    unittest.main()
