from __future__ import annotations

from enrichment.tenacious.crunchbase import fetch_crunchbase as _fetch


def load(company: str) -> dict:
    data = _fetch(company)
    return {"signal": "crunchbase", "confidence": 0.8, "data": data}
