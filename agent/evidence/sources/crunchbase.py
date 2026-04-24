from __future__ import annotations

from enrichment.tenacious.crunchbase import fetch_crunchbase as _fetch


def load(company: str) -> dict:
    return _fetch(company)
