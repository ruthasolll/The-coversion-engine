from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_leadership(company: str) -> dict:
    query = quote_plus(f"{company} new CTO OR VP Engineering OR Chief Data Officer")
    source_url = f"https://duckduckgo.com/html/?q={query}"

    value = f"No public leadership-change signal found for {company}"
    confidence = 0.45
    status: str | int = "unknown"
    try:
        response = requests.get(
            source_url,
            timeout=20,
            headers={"User-Agent": "ConversionEngine/1.0 (+public-data-check)"},
        )
        status = response.status_code
        if response.ok:
            result_title = re.search(r'class="result__a".*?>(.*?)</a>', response.text, re.IGNORECASE | re.DOTALL)
            if result_title:
                cleaned = re.sub(r"<.*?>", "", result_title.group(1)).strip()
                value = f"Top leadership-change result: {cleaned[:170]}"
                confidence = 0.78
            if "cto" in response.text.lower() or "vp engineering" in response.text.lower():
                confidence = min(0.88, confidence + 0.08)
        else:
            value = f"Leadership search returned status {response.status_code} for {company}"
            confidence = 0.3
    except Exception as exc:
        logger.exception("leadership_fetch_failed")
        signal = {
            "signal": "leadership_change_detection",
            "value": f"Leadership search failed: {str(exc)}",
            "confidence": 0.1,
            "source": source_url,
            "timestamp": _utc_now(),
        }
        logger.info(
            "enrichment_event",
            extra={"signal": signal["signal"], "company": company, "status": "error", "confidence": signal["confidence"]},
        )
        return signal

    signal = {
        "signal": "leadership_change_detection",
        "value": value,
        "confidence": round(confidence, 2),
        "source": source_url,
        "timestamp": _utc_now(),
    }
    logger.info(
        "enrichment_event",
        extra={"signal": signal["signal"], "company": company, "status": status, "confidence": signal["confidence"]},
    )
    return signal
