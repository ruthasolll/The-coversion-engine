from __future__ import annotations

import json

from enrichment.competitor_gap.pipeline import generate_competitor_gap_brief


def main() -> None:
    target_hiring_signal_brief = {
        "company_name": "Example Company",
        "generated_at": "2026-04-25T00:00:00+00:00",
        "signals": {
            "crunchbase": {
                "timestamp": "2026-04-25T00:00:00+00:00",
                "source": "crunchbase",
                "confidence": 0.8,
                "evidence": ["Fintech platform expanding enterprise payment tools."],
                "funding_stage": "SERIES B",
                "last_funding_date": "2025-06-01",
                "investors": ["Growth Partners"],
            },
            "jobs": {
                "timestamp": "2026-04-25T00:00:00+00:00",
                "source": "jobs",
                "confidence": 0.6,
                "evidence": ["Public jobs page shows core engineering roles."],
                "job_count": 3,
                "job_titles": ["Backend Engineer", "Product Manager", "Data Analyst"],
                "job_velocity_60d": 1,
            },
            "layoffs": {
                "timestamp": "2026-04-25T00:00:00+00:00",
                "source": "layoffs",
                "confidence": 0.3,
                "evidence": ["No layoffs detected."],
                "last_layoff_date": None,
                "total_layoffs_12m": 0,
                "severity_score": 0.0,
            },
            "leadership": {
                "timestamp": "2026-04-25T00:00:00+00:00",
                "source": "leadership",
                "confidence": 0.5,
                "evidence": ["Leadership continuity update with no explicit AI narrative."],
                "change_detected": False,
                "role_changed": None,
                "date": None,
            },
        },
    }

    brief = generate_competitor_gap_brief(
        target_company_name="Example Company",
        sector="fintech",
        target_hiring_signal_brief=target_hiring_signal_brief,
    )
    print(json.dumps(brief, indent=2))

    competitors = brief.get("competitors", [])
    fallback_used = bool(brief.get("fallback_used", False))
    assert (5 <= len(competitors) <= 10) or fallback_used, "Expected 5-10 competitors or fallback usage."
    assert isinstance(brief.get("distribution"), dict), "Distribution payload is required."
    assert 2 <= len(brief.get("gaps", [])) <= 3, "Expected 2-3 gaps."
    assert len(brief.get("competitor_scores", [])) == len(competitors), "Every competitor must be scored."


if __name__ == "__main__":
    main()

