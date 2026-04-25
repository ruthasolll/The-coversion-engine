from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from agent.channel_handoff import ChannelHandoffManager


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChannelEvent:
    channel: str
    event_type: str
    entity_id: str
    direction: str
    provider: str
    timestamp: str
    payload: dict

    @property
    def email(self) -> str:
        return self.entity_id


EmailEvent = ChannelEvent


class EmailEventEmitter(Protocol):
    def emit(self, event: ChannelEvent) -> dict:
        raise NotImplementedError


class HandoffEventEmitter:
    def __init__(self, handoff: ChannelHandoffManager | None = None) -> None:
        self.handoff = handoff or ChannelHandoffManager()

    def emit(self, event: ChannelEvent) -> dict:
        return self.handoff.process_event(
            {
                "channel": event.channel,
                "event_type": event.event_type,
                "entity_id": event.entity_id,
                "direction": event.direction,
                "provider": event.provider,
                "timestamp": event.timestamp,
                "payload": event.payload,
            }
        )


class HandoffEmailEventEmitter(HandoffEventEmitter):
    pass


def build_channel_event(
    *,
    channel: str,
    event_type: str,
    entity_id: str,
    direction: str,
    provider: str,
    payload: dict | None = None,
    timestamp: str | None = None,
) -> ChannelEvent:
    return ChannelEvent(
        channel=channel,
        event_type=event_type,
        entity_id=entity_id,
        direction=direction,
        provider=provider,
        timestamp=timestamp or _utc_now(),
        payload=payload or {},
    )


def build_email_event(*, event_type: str, email: str, provider: str, payload: dict | None = None, timestamp: str | None = None) -> EmailEvent:
    return build_channel_event(
        channel="email",
        event_type=event_type,
        entity_id=email,
        direction="inbound",
        provider=provider,
        payload=payload,
        timestamp=timestamp,
    )
