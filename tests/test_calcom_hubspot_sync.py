from __future__ import annotations

import unittest
from unittest.mock import patch

from calendars.webhook import process_calcom_booking_event


class FakeHubSpot:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.calls: list[dict] = []

    def update_contact_properties_by_email(self, email: str, properties: dict) -> dict:
        self.calls.append({"email": email, "properties": properties})
        if self.ok:
            return {"ok": True, "contact_id": "contact-123", "email": email}
        return {"ok": False, "error": "contact_not_found", "email": email}

    def record_activity_by_email(self, email: str, activity_type: str, details: dict) -> dict:
        return {"ok": True, "action": "activity_logged", "activity_type": activity_type, "email": email}


class CalComHubSpotSyncTests(unittest.TestCase):
    def test_completed_booking_updates_hubspot_contact(self) -> None:
        hubspot = FakeHubSpot(ok=True)
        payload = {
            "triggerEvent": "BOOKING_CREATED",
            "payload": {
                "id": "booking-abc",
                "bookingUrl": "https://cal.com/bookings/booking-abc",
                "startTime": "2026-04-23T14:00:00+03:00",
                "attendee": {"email": "lead@example.org"},
            },
        }
        result = process_calcom_booking_event(payload, hubspot=hubspot)
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "hubspot_updated")
        self.assertEqual(hubspot.calls[0]["email"], "lead@example.org")
        self.assertEqual(hubspot.calls[0]["properties"]["calcom_booking_id"], "booking-abc")

    def test_non_booking_event_is_ignored(self) -> None:
        hubspot = FakeHubSpot(ok=True)
        result = process_calcom_booking_event({"event": "PING"}, hubspot=hubspot)
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "ignored_non_booking_event")
        self.assertEqual(hubspot.calls, [])

    @patch("channels.email.resend_adapter.ResendAdapter.send_email")
    def test_booking_can_trigger_optional_notification(self, mocked_send_email) -> None:
        mocked_send_email.return_value = {"ok": True, "provider": "resend"}
        hubspot = FakeHubSpot(ok=True)
        payload = {
            "triggerEvent": "BOOKING_CREATED",
            "notify_booking_email": "true",
            "payload": {
                "id": "booking-abc",
                "bookingUrl": "https://cal.com/bookings/booking-abc",
                "startTime": "2026-04-23T14:00:00+03:00",
                "attendee": {"email": "lead@example.org"},
            },
        }
        result = process_calcom_booking_event(payload, hubspot=hubspot)
        self.assertTrue(result["ok"])
        self.assertTrue(result["notification"]["ok"])

    def test_missing_email_fails(self) -> None:
        hubspot = FakeHubSpot(ok=True)
        payload = {"triggerEvent": "BOOKING_CONFIRMED", "payload": {"id": "booking-abc"}}
        result = process_calcom_booking_event(payload, hubspot=hubspot)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_attendee_email")


if __name__ == "__main__":
    unittest.main()
