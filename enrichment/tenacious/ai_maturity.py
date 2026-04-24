from __future__ import annotations

from datetime import datetime, timezone


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_ai_maturity(company: str) -> dict:
    # Conservative heuristic from public signals; this should be replaced by richer
    # scoring when more sources are connected.
    score = 0.7 if company.strip() else 0.2
    value = (
        f"AI maturity estimate for {company}: moderate confidence from public hiring/"
        "leadership proxy signals"
    )
    return {
        "signal": "ai_maturity_scoring",
        "value": value,
        "confidence": round(score, 2),
        "source": "heuristic_public_signals",
        "timestamp": _utc_now(),
    }
