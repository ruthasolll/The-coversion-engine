from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LeadScore:
    value: float
    reason: str


def compute_score(signals: dict) -> LeadScore:
    raw = sum(float(v) for v in signals.values() if isinstance(v, (int, float)))
    score = min(1.0, max(0.0, raw / 10.0))
    return LeadScore(value=score, reason="normalized_signal_sum")
