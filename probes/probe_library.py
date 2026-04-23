from __future__ import annotations


def probe_stop_unsub(text: str) -> bool:
    return text.strip().lower() in {"stop", "unsubscribe", "cancel"}
