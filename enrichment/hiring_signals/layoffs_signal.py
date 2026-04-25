from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from enrichment.hiring_signals.schema import LayoffsSignal, utc_now_iso

logger = logging.getLogger(__name__)

_DEFAULT_LAYOFFS_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "layoffs.csv"


def _parse_date(value: str) -> datetime | None:
    """Parse a layoff date using a small set of accepted formats."""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _read_rows(csv_path: Path | None = None, csv_url: str | None = None) -> list[dict[str, str]]:
    """Read layoff rows from a local CSV or URL."""
    if csv_url:
        response = requests.get(csv_url, timeout=20)
        response.raise_for_status()
        raw = response.text.splitlines()
        return list(csv.DictReader(raw))
    path = csv_path or _DEFAULT_LAYOFFS_PATH
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file_handle:
        return list(csv.DictReader(file_handle))


def fetch_layoffs_signal(company_name: str, csv_path: Path | None = None, csv_url: str | None = None) -> LayoffsSignal:
    """Parse layoffs.fyi data and compute 12-month layoff signal."""
    timestamp = utc_now_iso()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=365)
    normalized_company = company_name.strip().lower()

    try:
        rows = _read_rows(csv_path=csv_path, csv_url=csv_url)
    except Exception as exc:
        logger.exception("layoffs_signal_read_failed")
        return LayoffsSignal(
            timestamp=timestamp,
            source="layoffs",
            confidence=0.1,
            evidence=[f"Failed to read layoffs dataset: {exc}"],
            last_layoff_date=None,
            total_layoffs_12m=0,
            severity_score=0.0,
        )

    if not rows:
        return LayoffsSignal(
            timestamp=timestamp,
            source="layoffs",
            confidence=0.0,
            evidence=["No layoffs dataset rows available."],
            last_layoff_date=None,
            total_layoffs_12m=0,
            severity_score=0.0,
        )

    company_rows: list[dict[str, str]] = []
    for row in rows:
        row_company = str(row.get("Company", "")).strip().lower()
        if normalized_company and normalized_company in row_company:
            company_rows.append(row)

    if not company_rows:
        return LayoffsSignal(
            timestamp=timestamp,
            source="layoffs",
            confidence=0.3,
            evidence=[f"No layoffs detected for {company_name} in available data."],
            last_layoff_date=None,
            total_layoffs_12m=0,
            severity_score=0.0,
        )

    total_12m = 0
    dates: list[datetime] = []
    evidence: list[str] = []
    for row in company_rows:
        parsed_date = _parse_date(str(row.get("Date", "")))
        if parsed_date is None:
            continue
        dates.append(parsed_date)
        if parsed_date >= cutoff:
            size_raw = str(row.get("Laid_Off_Count", "")).strip()
            size = int(size_raw) if size_raw.isdigit() else 0
            total_12m += size
            evidence.append(
                f"Layoff event on {parsed_date.date().isoformat()} with reported size {size}."
            )

    last_layoff = max(dates).date().isoformat() if dates else None
    severity_score = min(1.0, round((total_12m / 10000.0) + (len(evidence) * 0.08), 2))
    confidence = 0.85 if evidence else 0.6
    if not evidence:
        evidence.append("Company appears in layoffs dataset but no 12-month numeric events were found.")

    return LayoffsSignal(
        timestamp=timestamp,
        source="layoffs",
        confidence=confidence,
        evidence=evidence[:8],
        last_layoff_date=last_layoff,
        total_layoffs_12m=total_12m,
        severity_score=severity_score,
    )

