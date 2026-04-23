from __future__ import annotations

from playwright.sync_api import sync_playwright


def fetch_job_signals(url: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        title = page.title()
        browser.close()
    return {"source": "jobs", "url": url, "title": title}
