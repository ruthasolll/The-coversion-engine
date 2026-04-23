from __future__ import annotations

from datetime import datetime, timezone

from agent.evidence.sources.ai_maturity import load as ai_maturity
from agent.evidence.sources.crunchbase import load as crunchbase
from agent.evidence.sources.job_posts import load as jobs
from agent.evidence.sources.layoffs import load as layoffs
from agent.evidence.sources.leadership import load as leadership


def build_signal_artifact(*, company: str, jobs_url: str) -> dict:
    signals = [
        crunchbase(company),
        jobs(jobs_url),
        layoffs(company),
        leadership(company),
        ai_maturity(company),
    ]

    overall_confidence = round(sum(float(s["confidence"]) for s in signals) / len(signals), 3)

    return {
        "company": company,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "overall_confidence": overall_confidence,
        "schema_version": "v1",
    }
