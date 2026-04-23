from __future__ import annotations

from playwright.sync_api import sync_playwright


def fetch_job_signals(url: str) -> dict:
    # Compliance note: this loader only fetches public pages and does not perform
    # login flows or captcha bypass behavior.
    if "login" in url.lower():
        return {"source": "jobs", "url": url, "blocked": True, "reason": "login_pages_not_supported"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        title = page.title()
        body_preview = page.text_content("body") or ""
        browser.close()
    return {
        "source": "jobs",
        "url": url,
        "title": title,
        "preview": body_preview[:300],
        "compliance": {"uses_login": False, "uses_captcha_bypass": False},
    }
