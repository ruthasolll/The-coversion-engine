from __future__ import annotations


def bench_ready(payload: dict) -> bool:
    return bool(payload.get("lead_id")) and bool(payload.get("message"))
