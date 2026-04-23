from __future__ import annotations


def passes_confidence(payload: dict, threshold: float = 0.7) -> bool:
    score = float(payload.get("confidence", 0.0))
    return score >= threshold
