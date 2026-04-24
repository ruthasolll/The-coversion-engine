from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(company: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\\s-]", "", company).strip().lower()
    return re.sub(r"[\\s_]+", "-", cleaned)


def fetch_crunchbase(company: str) -> dict:
    company = company.strip()
    if not company:
        return {
            "signal": "crunchbase_firmographics",
            "value": "missing_company",
            "confidence": 0.0,
            "source": "crunchbase",
            "timestamp": _utc_now(),
        }

    org_url = f"https://www.crunchbase.com/organization/{_slug(company)}"
    value = f"No verified Crunchbase profile found for {company}"
    confidence = 0.25
    try:
        response = requests.get(
            org_url,
            timeout=20,
            headers={"User-Agent": "ConversionEngine/1.0 (+public-data-check)"},
        )
        if response.ok:
            title_match = re.search(r"<title>(.*?)</title>", response.text, re.IGNORECASE | re.DOTALL)
            page_title = title_match.group(1).strip() if title_match else ""
            if page_title:
                value = f"Crunchbase profile title: {page_title[:160]}"
                confidence = 0.82
            if "funding" in response.text.lower():
                value = f"{value}; funding references detected"
                confidence = min(0.92, confidence + 0.08)
        else:
            value = f"Crunchbase request returned status {response.status_code} for {company}"
            confidence = 0.3
    except requests.RequestException as exc:
        logger.exception("crunchbase_fetch_failed company=%s", company)
        value = f"Crunchbase fetch failed for {company}: {exc}"
        confidence = 0.15

    return {
        "signal": "crunchbase_firmographics",
        "value": value,
        "confidence": round(confidence, 2),
        "source": org_url,
        "timestamp": _utc_now(),
    }
