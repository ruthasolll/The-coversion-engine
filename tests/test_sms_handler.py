from __future__ import annotations

import unittest

from agent.handlers.sms import SMSDownstream, handle_africastalking_inbound, send_outbound_sms


class RecordingDownstream(SMSDownstream):
    def __init__(self) -> None:
        self.events: list[dict] = []

    def handle(self, event):  # type: ignore[override]
        self.events.append(
            {
                "event_type": event.event_type,
                "phone": event.phone,
                "provider": event.provider,
                "text": event.text,
            }
        )
        return {"accepted": True, "event_type": event.event_type}


class SMSHandlerTests(unittest.TestCase):
    def test_inbound_sms_forwards_to_downstream(self) -> None:
        downstream = RecordingDownstream()
        result = handle_africastalking_inbound(
            {"from": "+254700000001", "text": "Can we talk on Tuesday?"},
            downstream=downstream,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "forwarded")
        self.assertEqual(downstream.events[0]["event_type"], "sms.inbound")

    def test_stop_message_marks_stop_event(self) -> None:
        downstream = RecordingDownstream()
        result = handle_africastalking_inbound(
            {"from": "+254700000001", "text": "STOP"},
            downstream=downstream,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(downstream.events[0]["event_type"], "sms.stop_or_unsubscribe")

    def test_outbound_sms_blocked_without_email_reply(self) -> None:
        result = send_outbound_sms(
            phone="+254700000001",
            message="Checking in.",
            payload={"warm_lead": True, "email_replied": False},
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.status_code, 403)
        self.assertEqual(result.message, "sms_blocked_email_reply_required")


if __name__ == "__main__":
    unittest.main()
