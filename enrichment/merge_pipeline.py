from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from enrichment.tenacious.ai_maturity import estimate_ai_maturity
from enrichment.tenacious.crunchbase import fetch_crunchbase
from enrichment.tenacious.jobs import fetch_job_signals
from enrichment.tenacious.layoffs import fetch_layoff_signals
from enrichment.tenacious.leadership import fetch_leadership

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_confidence(signal: dict) -> float:
    try:
        value = float(signal.get("confidence", 0.0))
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


def _safe_signal(fetcher, signal_name: str, fallback_source: str, *args) -> dict:
    try:
        signal = fetcher(*args)
        if not isinstance(signal, dict):
            raise ValueError("signal must be a dict")
        required = {"signal", "value", "confidence", "source", "timestamp"}
        if not required.issubset(signal.keys()):
            missing = sorted(required - set(signal.keys()))
            raise ValueError(f"signal missing fields: {missing}")
        return signal
    except Exception as exc:
        logger.exception("enrichment_signal_failed", extra={"signal": signal_name})
        return {
            "signal": signal_name,
            "value": f"{signal_name} failed: {str(exc)}",
            "confidence": 0.1,
            "source": fallback_source,
            "timestamp": _utc_now(),
        }


def build_enrichment_artifact(company: str, jobs_url: str) -> dict:
    signals = [
        _safe_signal(fetch_crunchbase, "crunchbase_firmographics", "https://www.crunchbase.com", company),
        _safe_signal(fetch_job_signals, "job_post_velocity", jobs_url, jobs_url),
        _safe_signal(fetch_layoff_signals, "layoffs_fyi", "data/raw/layoffs.csv", company),
        _safe_signal(fetch_leadership, "leadership_change_detection", "https://duckduckgo.com", company),
        _safe_signal(estimate_ai_maturity, "ai_maturity_scoring", "heuristic_public_signals", company),
    ]
    overall_confidence = round(sum(_safe_confidence(s) for s in signals) / len(signals), 3)
    return {
        "company": company,
        "signals": signals,
        "overall_confidence": overall_confidence,
        "generated_at": _utc_now(),
    }


def save_enrichment_artifact(artifact: dict, output_path: Path | None = None) -> Path:
    if output_path is None:
        output_path = Path(__file__).resolve().parents[1] / "deliverables" / "enrichment_signal_artifact.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return output_path
