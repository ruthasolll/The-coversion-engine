from __future__ import annotations

import os
from dataclasses import dataclass

from channels.sms.africastalking_adapter import AfricasTalkingAdapter


@dataclass
class SMSSendResult:
    ok: bool
    provider: str
    status_code: int
    message: str
    dry_run: bool = False


class AfricasTalkingSMSClient:
    def _allow_real_contact(self) -> bool:
        return os.getenv("ALLOW_REAL_PROSPECT_CONTACT", "false").strip().lower() == "true"

    def send(self, phone: str, message: str) -> SMSSendResult:
        if not self._allow_real_contact():
            return SMSSendResult(
                ok=True,
                provider="africastalking",
                status_code=200,
                message="dry_run_kill_switch_enabled",
                dry_run=True,
            )

        adapter = AfricasTalkingAdapter()
        response = adapter.send_sms(phone=phone, message=message)
        if not response.get("ok", False):
            return SMSSendResult(
                ok=False,
                provider="africastalking",
                status_code=int(response.get("status_code", 400)),
                message=str(response.get("error", response.get("body", "sms_send_failed"))),
            )
        return SMSSendResult(
            ok=True,
            provider="africastalking",
            status_code=int(response.get("status_code", 200)),
            message="sent",
        )
