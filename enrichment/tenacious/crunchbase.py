from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(company: str) -> str:
    company = company.strip().lower()
    company = re.sub(r"[^a-z0-9\s_-]", "", company)
    company = re.sub(r"[\s_]+", "-", company)
    return company.strip("-")


def fetch_crunchbase(company: str) -> dict:
    company = company.strip()
    if not company:
        signal = {
            "signal": "crunchbase_firmographics",
            "value": "missing_company",
            "confidence": 0.0,
            "source": "crunchbase",
            "timestamp": _utc_now(),
        }
        logger.info(
            "enrichment_event",
            extra={"signal": signal["signal"], "company": company, "status": "missing_company", "confidence": signal["confidence"]},
        )
        return signal

    org_url = f"https://www.crunchbase.com/organization/{_slug(company)}"
    value = f"No verified Crunchbase profile found for {company}"
    confidence = 0.25
    status: str | int = "unknown"
    try:
        response = requests.get(
            org_url,
            timeout=20,
            headers={"User-Agent": "ConversionEngine/1.0 (+public-data-check)"},
        )
        status = response.status_code
        if response.ok:
            title_match = re.search(r"<title>(.*?)</title>", response.text, re.IGNORECASE | re.DOTALL)
            page_title = title_match.group(1).strip() if title_match else ""
            if page_title:
                value = f"Crunchbase profile title: {page_title[:160]}"
                confidence = 0.82
            if "funding" in response.text.lower():
                value = f"{value}; funding references detected"
                confidence = min(0.92, confidence + 0.08)
        elif response.status_code == 403:
            value = f"Crunchbase blocked request (anti-bot protection) for {company}"
            confidence = 0.4
        else:
            value = f"Crunchbase request returned status {response.status_code} for {company}"
            confidence = 0.3
    except Exception as exc:
        logger.exception("crunchbase_fetch_failed company=%s", company)
        signal = {
            "signal": "crunchbase_firmographics",
            "value": f"Crunchbase fetch failed: {str(exc)}",
            "confidence": 0.1,
            "source": org_url,
            "timestamp": _utc_now(),
        }
        logger.info(
            "enrichment_event",
            extra={"signal": signal["signal"], "company": company, "status": "error", "confidence": signal["confidence"]},
        )
        return signal

    signal = {
        "signal": "crunchbase_firmographics",
        "value": value,
        "confidence": round(confidence, 2),
        "source": org_url,
        "timestamp": _utc_now(),
    }
    logger.info(
        "enrichment_event",
        extra={"signal": signal["signal"], "company": company, "status": status, "confidence": signal["confidence"]},
    )
    return signal
