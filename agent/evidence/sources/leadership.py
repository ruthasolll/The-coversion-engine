from __future__ import annotations

from enrichment.tenacious.leadership import fetch_leadership as _fetch


def load(company: str) -> dict:
    return _fetch(company)
