from __future__ import annotations

import unittest

from agent.routing import select_channel


class SMSRoutingTests(unittest.TestCase):
    def test_phone_only_cold_lead_blocks_sms(self) -> None:
        channel, reason = select_channel({"phone": "+254700000000", "lead_temperature": "cold"})
        self.assertEqual(channel, "voice")
        self.assertEqual(reason, "sms_blocked_not_warm_lead")

    def test_phone_only_warm_lead_allows_sms(self) -> None:
        channel, reason = select_channel({"phone": "+254700000000", "lead_temperature": "warm"})
        self.assertEqual(channel, "sms")
        self.assertEqual(reason, "phone_only_warm_lead")

    def test_preferred_sms_cold_falls_back_to_email(self) -> None:
        channel, reason = select_channel(
            {
                "phone": "+254700000000",
                "email": "lead@example.org",
                "preferred_channel": "sms",
                "lead_temperature": "cold",
            }
        )
        self.assertEqual(channel, "email")
        self.assertEqual(reason, "sms_blocked_not_warm_lead_fallback_email")


if __name__ == "__main__":
    unittest.main()
