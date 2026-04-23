from __future__ import annotations


def fetch_news(company: str) -> dict:
    return {"company": company, "source": "news", "status": "stub"}
