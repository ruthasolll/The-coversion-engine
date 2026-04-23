from __future__ import annotations


def fetch_layoff_signals(company: str) -> dict:
    return {"company": company, "source": "layoffs", "status": "stub"}
