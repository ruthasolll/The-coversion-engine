from __future__ import annotations

from enrichment.tenacious.layoffs import fetch_layoff_signals as _fetch


def load(company: str) -> dict:
    data = _fetch(company)
    return {"signal": "layoffs", "confidence": 0.68, "data": data}
