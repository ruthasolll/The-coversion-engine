from __future__ import annotations

from enrichment.tenacious.ai_maturity import estimate_ai_maturity as _fetch


def load(company: str) -> dict:
    data = _fetch(company)
    return {"signal": "ai_maturity", "confidence": 0.7, "data": data}
