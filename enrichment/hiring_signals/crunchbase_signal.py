from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from enrichment.hiring_signals.schema import CrunchbaseSignal, utc_now_iso

logger = logging.getLogger(__name__)

_FUNDING_RANK = {
    "pre-seed": 0,
    "seed": 1,
    "series a": 2,
    "series b": 3,
    "series c": 4,
    "series d": 5,
    "series e": 6,
    "ipo": 7,
    "post-ipo": 8,
}


def _slug(company_name: str) -> str:
    """Convert a company name to a Crunchbase organization slug."""
    normalized = company_name.strip().lower()
    normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
    normalized = re.sub(r"[\s_]+", "-", normalized)
    return normalized.strip("-")


def _extract_json_ld(text: str) -> list[dict[str, Any]]:
    """Parse JSON-LD blocks from HTML."""
    blocks = re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    items: list[dict[str, Any]] = []
    for block in blocks:
        try:
            payload = json.loads(block.strip())
            if isinstance(payload, dict):
                items.append(payload)
            elif isinstance(payload, list):
                items.extend(item for item in payload if isinstance(item, dict))
        except json.JSONDecodeError:
            continue
    return items


def _extract_funding_stage(text: str) -> str | None:
    """Detect likely funding stage from Crunchbase page text."""
    patterns = [
        r"series\s+[a-z]",
        r"post-ipo",
        r"pre-ipo",
        r"\bipo\b",
        r"seed",
        r"pre-seed",
    ]
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            return match.group(0).upper().replace("PRE-IPO", "Pre-IPO").replace("POST-IPO", "Post-IPO")
    return None


def _extract_last_funding_date(text: str) -> str | None:
    """Extract likely funding date in YYYY-MM-DD format."""
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    return match.group(1) if match else None


def _extract_investors(text: str) -> list[str]:
    """Extract investor names from Crunchbase page text heuristically."""
    candidates = re.findall(
        r"\b([A-Z][A-Za-z0-9&.\- ]{2,40}(?:Capital|Ventures|Partners|Fund|Holdings))\b",
        text,
    )
    unique: list[str] = []
    for name in candidates:
        cleaned = " ".join(name.split())
        if cleaned not in unique:
            unique.append(cleaned)
    return unique[:8]


def _passes_funding_filter(stage: str | None) -> bool:
    """Return True when a company is at Series A+ or already public."""
    if not stage:
        return False
    normalized = stage.strip().lower()
    if normalized.startswith("series "):
        return _FUNDING_RANK.get(normalized, -1) >= _FUNDING_RANK["series a"]
    return normalized in {"post-ipo", "ipo", "pre-ipo"}


def fetch_crunchbase_signal(company_name: str) -> CrunchbaseSignal:
    """Fetch Crunchbase ODM-style firmographic and funding signal."""
    timestamp = utc_now_iso()
    company_name = company_name.strip()
    if not company_name:
        return CrunchbaseSignal(
            timestamp=timestamp,
            source="crunchbase",
            confidence=0.0,
            evidence=["Missing company name."],
            funding_stage=None,
            last_funding_date=None,
            investors=[],
            funding_filter_passed=False,
        )

    slug = _slug(company_name)
    org_url = f"https://www.crunchbase.com/organization/{slug}"
    try:
        response = requests.get(
            org_url,
            timeout=20,
            headers={"User-Agent": "ConversionEngine/1.0 (+hiring-signal-enrichment)"},
        )
    except Exception as exc:
        logger.exception("crunchbase_signal_request_failed")
        return CrunchbaseSignal(
            timestamp=timestamp,
            source="crunchbase",
            confidence=0.1,
            evidence=[f"Crunchbase request failed: {exc}"],
            funding_stage=None,
            last_funding_date=None,
            investors=[],
            funding_filter_passed=False,
        )

    if response.status_code == 404:
        return CrunchbaseSignal(
            timestamp=timestamp,
            source="crunchbase",
            confidence=0.0,
            evidence=[f"No Crunchbase record found for {company_name}."],
            funding_stage=None,
            last_funding_date=None,
            investors=[],
            funding_filter_passed=False,
        )

    if response.status_code == 403:
        return CrunchbaseSignal(
            timestamp=timestamp,
            source="crunchbase",
            confidence=0.25,
            evidence=[f"Crunchbase blocked the request for {company_name} (403)."],
            funding_stage=None,
            last_funding_date=None,
            investors=[],
            funding_filter_passed=False,
        )

    if not response.ok:
        return CrunchbaseSignal(
            timestamp=timestamp,
            source="crunchbase",
            confidence=0.2,
            evidence=[f"Crunchbase request returned status {response.status_code}."],
            funding_stage=None,
            last_funding_date=None,
            investors=[],
            funding_filter_passed=False,
        )

    page_text = response.text
    _ = _extract_json_ld(page_text)
    stage = _extract_funding_stage(page_text)
    investors = _extract_investors(page_text)
    last_funding_date = _extract_last_funding_date(page_text)
    filter_passed = _passes_funding_filter(stage)

    evidence = [f"Crunchbase organization page parsed from {org_url}."]
    if stage:
        evidence.append(f"Detected funding stage: {stage}.")
    if last_funding_date:
        evidence.append(f"Detected funding date: {last_funding_date}.")
    if investors:
        evidence.append(f"Detected investors: {', '.join(investors[:3])}.")
    if not stage:
        evidence.append("Funding stage not clearly present in public content.")

    confidence = 0.5
    if stage and last_funding_date:
        confidence = 0.9 if filter_passed else 0.7
    elif stage or investors:
        confidence = 0.65 if filter_passed else 0.55

    return CrunchbaseSignal(
        timestamp=timestamp,
        source="crunchbase",
        confidence=confidence,
        evidence=evidence,
        funding_stage=stage,
        last_funding_date=last_funding_date,
        investors=investors,
        funding_filter_passed=filter_passed,
    )

