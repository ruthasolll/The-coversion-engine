from __future__ import annotations

from enrichment.tenacious.jobs import fetch_job_signals as _fetch


def load(url: str) -> dict:
    return _fetch(url)
