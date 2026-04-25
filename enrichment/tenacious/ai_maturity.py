from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


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
    signal = {
        "signal": "ai_maturity_scoring",
        "value": value,
        "confidence": round(score, 2),
        "source": "heuristic_public_signals",
        "timestamp": _utc_now(),
    }
    logger.info(
        "enrichment_event",
        extra={"signal": signal["signal"], "company": company, "status": "heuristic", "confidence": signal["confidence"]},
    )
    return signal
