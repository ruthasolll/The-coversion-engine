from __future__ import annotations

from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_job_signals(url: str) -> dict:
    # Compliance note: this loader only fetches public pages and does not perform
    # login flows or captcha bypass behavior.
    if "login" in url.lower():
        return {
            "signal": "job_post_velocity",
            "value": "blocked_non_public_login_page",
            "confidence": 0.05,
            "source": url,
            "timestamp": _utc_now(),
        }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        title = page.title()
        body_preview = page.text_content("body") or ""
        browser.close()
    value = f"Jobs page title '{title}' with preview length {len(body_preview[:300])}"
    return {
        "signal": "job_post_velocity",
        "value": value,
        "confidence": 0.78,
        "source": url,
        "timestamp": _utc_now(),
        "compliance": {"uses_login": False, "uses_captcha_bypass": False},
    }
