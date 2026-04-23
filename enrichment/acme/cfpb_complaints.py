from __future__ import annotations


def fetch_cfpb_complaints(company: str) -> dict:
    return {"company": company, "source": "cfpb_complaints", "status": "stub"}
