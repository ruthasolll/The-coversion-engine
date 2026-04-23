from __future__ import annotations


def fetch_crunchbase(company: str) -> dict:
    return {"company": company, "source": "crunchbase", "status": "stub"}
