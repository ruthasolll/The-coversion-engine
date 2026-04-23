from __future__ import annotations

from enrichment.tenacious.leadership import fetch_leadership as _fetch


def load(company: str) -> dict:
    data = _fetch(company)
    return {"signal": "leadership", "confidence": 0.73, "data": data}
