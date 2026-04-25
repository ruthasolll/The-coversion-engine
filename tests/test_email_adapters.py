from __future__ import annotations

import unittest
from unittest.mock import patch

from channels.email.mailersend_adapter import MailerSendAdapter
from channels.email.resend_adapter import ResendAdapter


class RecordingEmitter:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit(self, event) -> dict:
        self.events.append(
            {
                "event_type": event.event_type,
                "email": event.email,
                "provider": event.provider,
            }
        )
        return {"ok": True, "action": "record_event_only"}


class FakeResponse:
    def __init__(self, ok: bool = True, status_code: int = 200, text: str = "{}") -> None:
        self.ok = ok
        self.status_code = status_code
        self.text = text


class EmailAdaptersTests(unittest.TestCase):
    @patch("channels.email.resend_adapter.requests.post")
    @patch("channels.email.resend_adapter.os.getenv")
    def test_resend_emits_email_sent_event(self, mock_getenv, mock_post) -> None:
        mock_getenv.side_effect = lambda key, default="": {
            "RESEND_API_KEY": "k",
            "RESEND_FROM_EMAIL": "from@example.org",
        }.get(key, default)
        mock_post.return_value = FakeResponse(ok=True, status_code=200, text='{"id":"1"}')
        emitter = RecordingEmitter()

        result = ResendAdapter().send_email("lead@example.org", "Hi", "<p>hello</p>", emitter=emitter)  # type: ignore[arg-type]
        self.assertTrue(result["ok"])
        self.assertEqual(result["event"], "email_sent")
        self.assertEqual(emitter.events[0]["provider"], "resend")

    @patch("channels.email.mailersend_adapter.requests.post")
    @patch("channels.email.mailersend_adapter.os.getenv")
    def test_mailersend_emits_email_sent_event(self, mock_getenv, mock_post) -> None:
        mock_getenv.side_effect = lambda key, default="": {
            "MAILERSEND_API_KEY": "k",
            "MAILERSEND_FROM_EMAIL": "from@example.org",
            "MAILERSEND_REPLY_TO": "reply@example.org",
        }.get(key, default)
        mock_post.return_value = FakeResponse(ok=True, status_code=202, text='{"id":"1"}')
        emitter = RecordingEmitter()

        result = MailerSendAdapter().send_email("lead@example.org", "Hi", "<p>hello</p>", emitter=emitter)  # type: ignore[arg-type]
        self.assertTrue(result["ok"])
        self.assertEqual(result["event"], "email_sent")
        self.assertEqual(emitter.events[0]["provider"], "mailersend")


if __name__ == "__main__":
    unittest.main()
