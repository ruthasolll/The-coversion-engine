from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.handlers.sms import handle_africastalking_inbound, send_outbound_sms


class FakeSendResult:
    def __init__(self, dry_run: bool = False) -> None:
        self.ok = True
        self.provider = "africastalking"
        self.status_code = 200
        self.message = "dry_run_kill_switch_enabled" if dry_run else "sent"
        self.dry_run = dry_run


class SMSHandlerTests(unittest.TestCase):
    @patch("agent.handlers.sms.HandoffEventEmitter.emit")
    def test_inbound_sms_emits_event(self, mocked_emit) -> None:
        mocked_emit.return_value = {"ok": True, "action": "sms_event_recorded"}
        result = handle_africastalking_inbound({"from": "+254700000001", "text": "Can we talk on Tuesday?"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "forwarded")
        self.assertEqual(result["event_type"], "sms.inbound")

    @patch("agent.handlers.sms.HandoffEventEmitter.emit")
    def test_stop_message_marks_stop_event(self, mocked_emit) -> None:
        mocked_emit.return_value = {"ok": True, "action": "sms_event_recorded"}
        result = handle_africastalking_inbound({"from": "+254700000001", "text": "STOP"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["event_type"], "sms.stop_or_unsubscribe")

    @patch("agent.channel_handoff.AfricasTalkingSMSClient.send")
    def test_outbound_sms_allowed_after_email_reply(self, mocked_send) -> None:
        mocked_send.return_value = FakeSendResult()
        result = send_outbound_sms(
            phone="+254700000001",
            message="Checking in.",
            payload={"email_replied": True},
        )
        self.assertTrue(result.ok)
        self.assertFalse(result.dry_run)

    @patch("agent.channel_handoff.AfricasTalkingSMSClient.send")
    def test_outbound_sms_dry_run_is_treated_as_success(self, mocked_send) -> None:
        mocked_send.return_value = FakeSendResult(dry_run=True)
        result = send_outbound_sms(
            phone="+254700000001",
            message="Checking in.",
            payload={"email_replied": True},
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.message, "dry_run_kill_switch_enabled")

    def test_outbound_sms_blocked_without_email_reply(self) -> None:
        result = send_outbound_sms(
            phone="+254700000001",
            message="Checking in.",
            payload={"email_replied": False},
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.status_code, 403)
        self.assertEqual(result.message, "sms_blocked_email_reply_required")


if __name__ == "__main__":
    unittest.main()
