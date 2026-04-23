from __future__ import annotations


STOP_WORDS = {"stop", "unsubscribe", "cancel"}


def should_stop_or_unsubscribe(payload: dict) -> bool:
    inbound = str(payload.get("inbound_text", "")).strip().lower()
    return inbound in STOP_WORDS
