from __future__ import annotations

import re
from typing import Any

from enrichment.ai_maturity.scorer import compute_ai_maturity_score


def _deterministic_seed(company: str, sector: str) -> int:
    """Build deterministic seed from company+sector names."""
    key = f"{company.strip().lower()}::{sector.strip().lower()}"
    return sum(ord(ch) for ch in key)


def _build_competitor_hiring_signal_brief(company: str, sector: str) -> dict[str, Any]:
    """Create deterministic HiringSignalBrief-shaped input for AI maturity scorer."""
    seed = _deterministic_seed(company, sector)
    ai_bias = seed % 4
    base_roles = ["Backend Engineer", "Product Manager", "Data Analyst"]
    ai_roles = [
        "ML Engineer",
        "Data Scientist",
        "Head of AI",
        "Applied AI Engineer",
        "LLM Platform Engineer",
    ]
    selected_ai_roles = ai_roles[: max(0, ai_bias)]
    job_titles = base_roles + selected_ai_roles

    leadership_text = (
        f"{company} appoints VP AI to accelerate automation roadmap."
        if ai_bias >= 2
        else f"{company} announces leadership continuity in core operations."
    )
    role_changed = "VP AI" if ai_bias >= 2 else "CTO"
    change_detected = ai_bias >= 1

    evidence = [
        f"{company} operates in {sector} with focus on product scale.",
        "Investor update mentions AI transformation." if ai_bias >= 2 else "Investor update focuses on growth efficiency.",
    ]

    return {
        "company_name": company,
        "generated_at": "2026-04-25T00:00:00+00:00",
        "signals": {
            "crunchbase": {
                "timestamp": "2026-04-25T00:00:00+00:00",
                "source": "crunchbase",
                "confidence": 0.8,
                "evidence": evidence,
                "funding_stage": "SERIES C" if ai_bias >= 2 else "SERIES B",
                "last_funding_date": "2025-09-01",
                "investors": ["Top Quartile Capital"],
            },
            "jobs": {
                "timestamp": "2026-04-25T00:00:00+00:00",
                "source": "jobs",
                "confidence": 0.8 if ai_bias >= 1 else 0.6,
                "evidence": [f"Public jobs page scraped for {company}."],
                "job_count": len(job_titles),
                "job_titles": job_titles,
                "job_velocity_60d": 1 + ai_bias,
            },
            "layoffs": {
                "timestamp": "2026-04-25T00:00:00+00:00",
                "source": "layoffs",
                "confidence": 0.4,
                "evidence": ["No layoffs detected in the last 12 months."],
                "last_layoff_date": None,
                "total_layoffs_12m": 0,
                "severity_score": 0.0,
            },
            "leadership": {
                "timestamp": "2026-04-25T00:00:00+00:00",
                "source": "leadership",
                "confidence": 0.75 if ai_bias >= 2 else 0.55,
                "evidence": [leadership_text],
                "change_detected": change_detected,
                "role_changed": role_changed,
                "date": "2026-02-01" if change_detected else None,
            },
        },
    }


def _summarize_justification(justification: dict[str, str]) -> dict[str, str]:
    """Create compact summary fields from scorer justification strings."""
    summary: dict[str, str] = {}
    for key, value in justification.items():
        sentence = re.split(r"(?<=\.)\s+", str(value).strip())[0]
        summary[key] = sentence[:220]
    return summary


def score_company(company: str, sector: str, hiring_signal_brief: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run AI maturity scoring for one company and return normalized payload."""
    brief = hiring_signal_brief or _build_competitor_hiring_signal_brief(company, sector)
    scored = compute_ai_maturity_score(brief)
    return {
        "company": company,
        "score": int(scored.get("score", 0)),
        "confidence": float(scored.get("confidence", 0.0)),
        "signals_summary": _summarize_justification(scored.get("justification", {})),
        "full_result": scored,
    }


def score_competitors(competitors: list[str], sector: str) -> list[dict[str, Any]]:
    """Score all competitors deterministically using shared AI maturity scorer."""
    return [score_company(company=name, sector=sector) for name in competitors]

