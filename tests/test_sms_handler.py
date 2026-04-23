from __future__ import annotations

import unittest

from agent.handlers.sms import SMSDownstream, handle_africastalking_inbound


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


if __name__ == "__main__":
    unittest.main()
