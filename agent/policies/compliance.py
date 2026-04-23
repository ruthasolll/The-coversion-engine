from __future__ import annotations


FORBIDDEN_TERMS = {"guaranteed returns", "not financial advice"}


def passes_compliance(payload: dict) -> bool:
    text = str(payload.get("message", "")).lower()
    return not any(term in text for term in FORBIDDEN_TERMS)
