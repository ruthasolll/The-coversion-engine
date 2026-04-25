from __future__ import annotations

from enrichment.hiring_signals.crunchbase_signal import fetch_crunchbase_signal
from enrichment.hiring_signals.jobs_signal import fetch_jobs_signal
from enrichment.hiring_signals.layoffs_signal import fetch_layoffs_signal
from enrichment.hiring_signals.leadership_signal import fetch_leadership_signal
from enrichment.hiring_signals.schema import HiringSignalBrief, clamp_confidence, utc_now_iso


def run_hiring_signal_pipeline(company_name: str) -> dict:
    """Orchestrate all hiring signal modules and return normalized brief."""
    generated_at = utc_now_iso()
    crunchbase_signal = fetch_crunchbase_signal(company_name)
    jobs_signal = fetch_jobs_signal(company_name)
    layoffs_signal = fetch_layoffs_signal(company_name)
    leadership_signal = fetch_leadership_signal(
        company_name,
        crunchbase_evidence=crunchbase_signal.evidence,
    )

    crunchbase_signal.confidence = clamp_confidence(crunchbase_signal.confidence)
    jobs_signal.confidence = clamp_confidence(jobs_signal.confidence)
    layoffs_signal.confidence = clamp_confidence(layoffs_signal.confidence)
    leadership_signal.confidence = clamp_confidence(leadership_signal.confidence)

    brief = HiringSignalBrief(
        company_name=company_name,
        generated_at=generated_at,
        crunchbase_signal=crunchbase_signal,
        jobs_signal=jobs_signal,
        layoffs_signal=layoffs_signal,
        leadership_signal=leadership_signal,
    )
    return brief.to_output()

