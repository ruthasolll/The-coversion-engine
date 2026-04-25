from __future__ import annotations

import json
import logging
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import robotparser
from urllib.parse import urlparse

import requests

from enrichment.hiring_signals.schema import JobsSignal, utc_now_iso

logger = logging.getLogger(__name__)

_HISTORY_FILE = Path(__file__).resolve().parent / "job_history.json"


def _slug(company_name: str) -> str:
    """Create URL-friendly slug."""
    normalized = company_name.strip().lower()
    normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
    normalized = re.sub(r"[\s_]+", "-", normalized)
    return normalized.strip("-")


def build_public_job_urls(company_name: str) -> list[str]:
    """Build public career URLs for target job sources."""
    slug = _slug(company_name)
    return [
        f"https://www.builtin.com/company/{slug}",
        f"https://wellfound.com/company/{slug}/jobs",
        f"https://www.linkedin.com/company/{slug}/jobs/",
    ]


def check_robots_txt(url: str, user_agent: str = "ConversionEngineBot") -> tuple[bool, str]:
    """Return whether scraping is allowed for URL path by robots.txt."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = robotparser.RobotFileParser()
    try:
        response = requests.get(
            robots_url,
            timeout=10,
            headers={"User-Agent": user_agent},
        )
        if not response.ok:
            return True, f"robots.txt unavailable ({response.status_code}); proceeding with caution."
        parser.parse(response.text.splitlines())
        allowed = parser.can_fetch(user_agent, url)
        return allowed, f"robots.txt check for {parsed.netloc}: {'allowed' if allowed else 'disallowed'}."
    except Exception as exc:
        return True, f"robots.txt check failed for {parsed.netloc}: {exc}; proceeding with caution."


def _extract_job_titles(page_text: str) -> list[str]:
    """Extract role-like titles from page text."""
    raw_titles = re.findall(
        r"\b([A-Z][A-Za-z/&+ .-]{2,70}(?:Engineer|Manager|Developer|Scientist|Designer|Recruiter|Director|Specialist|Analyst|Sales|Marketing|Product|Operations))\b",
        page_text,
    )
    unique: list[str] = []
    for title in raw_titles:
        cleaned = " ".join(title.split())
        if cleaned not in unique:
            unique.append(cleaned)
    return unique[:20]


def _load_history() -> dict[str, list[dict[str, Any]]]:
    """Load historical job snapshots from local JSON store."""
    if not _HISTORY_FILE.exists():
        return {}
    try:
        return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_history(history: dict[str, list[dict[str, Any]]]) -> None:
    """Persist historical snapshots safely."""
    _HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


def _select_60d_baseline(
    company_name: str,
    current_count: int,
    now: datetime,
    history: dict[str, list[dict[str, Any]]],
) -> tuple[int, bool]:
    """Return baseline count and flag showing whether historical baseline exists."""
    snapshots = history.get(company_name.lower(), [])
    cutoff = now - timedelta(days=60)
    historical = [
        item
        for item in snapshots
        if datetime.fromisoformat(str(item.get("timestamp")).replace("Z", "+00:00")) <= cutoff
    ]
    if historical:
        nearest = sorted(historical, key=lambda item: item["timestamp"], reverse=True)[0]
        return int(nearest.get("job_count", 0)), True

    rng = random.Random(company_name.lower())
    baseline = max(0, current_count - rng.randint(0, 3))
    return baseline, False


def _snapshot_history(company_name: str, current_count: int, now_iso: str, history: dict[str, list[dict[str, Any]]]) -> None:
    """Append current snapshot to history for future velocity comparisons."""
    key = company_name.lower()
    history.setdefault(key, [])
    history[key].append({"timestamp": now_iso, "job_count": current_count})
    history[key] = history[key][-20:]
    try:
        _save_history(history)
    except Exception:
        logger.exception("jobs_history_save_failed")


def fetch_jobs_signal(company_name: str) -> JobsSignal:
    """Scrape public job pages and compute 60-day job-post velocity."""
    now_iso = utc_now_iso()
    now_dt = datetime.fromisoformat(now_iso)
    urls = build_public_job_urls(company_name)
    all_titles: list[str] = []
    evidence: list[str] = []
    robots_allowed_count = 0
    scraped_sources = 0

    # Only public pages are scraped. No authentication bypass.
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return JobsSignal(
            timestamp=now_iso,
            source="jobs",
            confidence=0.1,
            evidence=[f"Playwright unavailable: {exc}"],
            job_count=0,
            job_titles=[],
            job_velocity_60d=0,
            baseline_job_count_60d=0,
        )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        for url in urls:
            allowed, robots_message = check_robots_txt(url)
            evidence.append(robots_message)
            if not allowed:
                continue
            robots_allowed_count += 1
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                text_content = page.text_content("body") or ""
                titles = _extract_job_titles(text_content)
                scraped_sources += 1
                all_titles.extend(titles)
                evidence.append(f"Scraped {len(titles)} role-like titles from {url}.")
            except Exception as exc:
                evidence.append(f"Failed to scrape {url}: {exc}")
        browser.close()

    unique_titles: list[str] = []
    for title in all_titles:
        if title not in unique_titles:
            unique_titles.append(title)
    unique_titles = unique_titles[:25]
    current_count = len(unique_titles)

    history = _load_history()
    baseline_count, has_historical_baseline = _select_60d_baseline(
        company_name=company_name,
        current_count=current_count,
        now=now_dt,
        history=history,
    )
    velocity = current_count - baseline_count
    _snapshot_history(company_name=company_name, current_count=current_count, now_iso=now_iso, history=history)

    if current_count == 0:
        confidence = 0.2
        evidence.append("Zero job posts detected across public sources.")
    elif has_historical_baseline:
        confidence = 0.9 if scraped_sources >= 2 else 0.8
        evidence.append("Velocity used historical snapshot older than 60 days.")
    else:
        confidence = 0.5
        evidence.append("No 60-day baseline found; simulated baseline used.")

    if robots_allowed_count == 0:
        confidence = min(confidence, 0.3)
        evidence.append("No sources were robots-allowed for scraping.")

    return JobsSignal(
        timestamp=now_iso,
        source="jobs",
        confidence=confidence,
        evidence=evidence,
        job_count=current_count,
        job_titles=unique_titles[:10],
        job_velocity_60d=velocity,
        baseline_job_count_60d=baseline_count,
    )

