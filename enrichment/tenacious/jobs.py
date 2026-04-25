from __future__ import annotations

import logging
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_job_signals(url: str) -> dict:
    # Compliance note: this loader only fetches public pages and does not perform
    # login flows or captcha bypass behavior.
    if "login" in url.lower():
        signal = {
            "signal": "job_post_velocity",
            "value": "blocked_non_public_login_page",
            "confidence": 0.05,
            "source": url,
            "timestamp": _utc_now(),
        }
        logger.info(
            "enrichment_event",
            extra={"signal": signal["signal"], "company": url, "status": "blocked_login", "confidence": signal["confidence"]},
        )
        return signal

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            title = page.title()
            body_preview = page.text_content("body") or ""
            browser.close()
        value = f"Jobs page title '{title}' with preview length {len(body_preview[:300])}"
        confidence = 0.78
        status = response.status if response else "no_response"
    except Exception as exc:
        logger.exception("jobs_fetch_failed")
        signal = {
            "signal": "job_post_velocity",
            "value": f"Jobs fetch failed: {str(exc)}",
            "confidence": 0.1,
            "source": url,
            "timestamp": _utc_now(),
            "compliance": {"uses_login": False, "uses_captcha_bypass": False},
        }
        logger.info(
            "enrichment_event",
            extra={"signal": signal["signal"], "company": url, "status": "error", "confidence": signal["confidence"]},
        )
        return signal

    signal = {
        "signal": "job_post_velocity",
        "value": value,
        "confidence": confidence,
        "source": url,
        "timestamp": _utc_now(),
        "compliance": {"uses_login": False, "uses_captcha_bypass": False},
    }
    logger.info(
        "enrichment_event",
        extra={"signal": signal["signal"], "company": url, "status": status, "confidence": signal["confidence"]},
    )
    return signal
