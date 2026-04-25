from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import requests

from enrichment.hiring_signals.schema import LeadershipSignal, utc_now_iso

logger = logging.getLogger(__name__)

_ROLE_PATTERN = re.compile(r"\b(CEO|CTO|CFO|COO|CMO|CPO|VP Engineering|Head of AI|Chief AI Officer)\b", re.IGNORECASE)
_CHANGE_PATTERN = re.compile(
    r"\b(appointed|joins as|hired as|named|promoted to|steps down|resigned|new)\b",
    re.IGNORECASE,
)


def _extract_date(text: str) -> str | None:
    """Extract date from free-form evidence text."""
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    return match.group(1) if match else None


def _fetch_press_mentions(company_name: str) -> list[str]:
    """Fetch public press snippets likely indicating leadership changes."""
    query = quote_plus(f"{company_name} new CEO OR CTO OR executive hire")
    url = f"https://duckduckgo.com/html/?q={query}"
    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "ConversionEngine/1.0 (+public-leadership-check)"},
    )
    response.raise_for_status()
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', response.text, flags=re.IGNORECASE | re.DOTALL)
    cleaned: list[str] = []
    for title in titles:
        text = re.sub(r"<.*?>", "", title)
        text = " ".join(text.split())
        if text:
            cleaned.append(text)
    return cleaned[:8]


def _detect_change(evidence_items: list[str]) -> tuple[bool, str | None, str | None]:
    """Detect leadership change from evidence lines."""
    detected_role: str | None = None
    detected_date: str | None = None
    for item in evidence_items:
        role_match = _ROLE_PATTERN.search(item)
        change_match = _CHANGE_PATTERN.search(item)
        if role_match and change_match:
            detected_role = role_match.group(1).upper()
            detected_date = _extract_date(item)
            return True, detected_role, detected_date
    return False, None, None


def fetch_leadership_signal(company_name: str, crunchbase_evidence: list[str] | None = None) -> LeadershipSignal:
    """Detect leadership changes from press + Crunchbase evidence."""
    timestamp = utc_now_iso()
    evidence: list[str] = []
    press_mentions: list[str] = []
    crunchbase_evidence = crunchbase_evidence or []

    try:
        press_mentions = _fetch_press_mentions(company_name)
        if press_mentions:
            evidence.append(f"Collected {len(press_mentions)} public press headlines.")
    except Exception as exc:
        logger.exception("leadership_press_fetch_failed")
        evidence.append(f"Public press lookup failed: {exc}")

    combined_evidence = press_mentions + crunchbase_evidence
    change_detected, role_changed, change_date = _detect_change(combined_evidence)

    if not change_detected:
        return LeadershipSignal(
            timestamp=timestamp,
            source="leadership",
            confidence=0.5,
            evidence=evidence + ["No leadership change detected from available sources."],
            change_detected=False,
            role_changed=None,
            date=None,
        )

    source_count = 0
    if _detect_change(press_mentions)[0]:
        source_count += 1
    if _detect_change(crunchbase_evidence)[0]:
        source_count += 1
    confidence = 0.85 if source_count >= 2 else 0.72

    return LeadershipSignal(
        timestamp=timestamp,
        source="leadership",
        confidence=confidence,
        evidence=evidence + [f"Detected role change for {role_changed or 'executive role'}."],
        change_detected=True,
        role_changed=role_changed,
        date=change_date,
    )

