from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from agent.channel_handoff import ChannelHandoffManager


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EmailEvent:
    event_type: str
    email: str
    provider: str
    timestamp: str
    payload: dict


class EmailEventEmitter(Protocol):
    def emit(self, event: EmailEvent) -> dict:
        raise NotImplementedError


class HandoffEmailEventEmitter:
    def __init__(self, handoff: ChannelHandoffManager | None = None) -> None:
        self.handoff = handoff or ChannelHandoffManager()

    def emit(self, event: EmailEvent) -> dict:
        return self.handoff.process_email_event(
            {
                "event_type": event.event_type,
                "email": event.email,
                "provider": event.provider,
                "timestamp": event.timestamp,
                "payload": event.payload,
            }
        )


def build_email_event(*, event_type: str, email: str, provider: str, payload: dict | None = None, timestamp: str | None = None) -> EmailEvent:
    return EmailEvent(
        event_type=event_type,
        email=email,
        provider=provider,
        timestamp=timestamp or _utc_now(),
        payload=payload or {},
    )
