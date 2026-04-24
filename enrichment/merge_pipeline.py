from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from enrichment.tenacious.ai_maturity import estimate_ai_maturity
from enrichment.tenacious.crunchbase import fetch_crunchbase
from enrichment.tenacious.jobs import fetch_job_signals
from enrichment.tenacious.layoffs import fetch_layoff_signals
from enrichment.tenacious.leadership import fetch_leadership


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_confidence(signal: dict) -> float:
    try:
        value = float(signal.get("confidence", 0.0))
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


def build_enrichment_artifact(company: str, jobs_url: str) -> dict:
    signals = [
        fetch_crunchbase(company),
        fetch_job_signals(jobs_url),
        fetch_layoff_signals(company),
        fetch_leadership(company),
        estimate_ai_maturity(company),
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
