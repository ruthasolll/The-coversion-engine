from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_layoff_signals(company: str) -> dict:
    company_norm = company.strip().lower()
    csv_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "layoffs.csv"
    if not csv_path.exists():
        signal = {
            "signal": "layoffs_fyi",
            "value": "layoffs dataset unavailable",
            "confidence": 0.0,
            "source": "data/raw/layoffs.csv",
            "timestamp": _utc_now(),
        }
        logger.info(
            "enrichment_event",
            extra={"signal": signal["signal"], "company": company, "status": "missing_dataset", "confidence": signal["confidence"]},
        )
        return signal

    try:
        latest_hit: dict | None = None
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                company_name = str(row.get("Company", "")).strip().lower()
                if company_norm and company_norm in company_name:
                    latest_hit = row

        if latest_hit:
            date = str(latest_hit.get("Date", "unknown")).strip()
            laid_off = str(latest_hit.get("Laid Off", "unknown")).strip()
            pct = str(latest_hit.get("%", "unknown")).strip()
            value = f"Layoff record found on {date}: laid_off={laid_off}, pct={pct}"
            confidence = 0.83
            status = "record_found"
        else:
            value = f"No layoffs.fyi record found for {company}"
            confidence = 0.62
            status = "no_record"
    except Exception as exc:
        logger.exception("layoffs_fetch_failed")
        signal = {
            "signal": "layoffs_fyi",
            "value": f"Layoffs fetch failed: {str(exc)}",
            "confidence": 0.1,
            "source": "data/raw/layoffs.csv",
            "timestamp": _utc_now(),
        }
        logger.info(
            "enrichment_event",
            extra={"signal": signal["signal"], "company": company, "status": "error", "confidence": signal["confidence"]},
        )
        return signal

    signal = {
        "signal": "layoffs_fyi",
        "value": value,
        "confidence": round(confidence, 2),
        "source": "data/raw/layoffs.csv",
        "timestamp": _utc_now(),
    }
    logger.info(
        "enrichment_event",
        extra={"signal": signal["signal"], "company": company, "status": status, "confidence": signal["confidence"]},
    )
    return signal
