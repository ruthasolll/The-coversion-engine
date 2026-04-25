from __future__ import annotations

from enrichment.ai_maturity.scorer import compute_ai_maturity_score


def main() -> None:
    sample_hiring_signal_brief = {
        "company_name": "ExampleCo",
        "generated_at": "2026-04-25T09:00:00+00:00",
        "signals": {
            "crunchbase": {
                "timestamp": "2026-04-25T09:00:00+00:00",
                "source": "crunchbase",
                "confidence": 0.82,
                "evidence": ["Series B funding announced in 2025."],
                "funding_stage": "SERIES B",
                "last_funding_date": "2025-08-01",
                "investors": ["Northstar Ventures"],
            },
            "jobs": {
                "timestamp": "2026-04-25T09:00:00+00:00",
                "source": "jobs",
                "confidence": 0.88,
                "evidence": ["Scraped public jobs pages."],
                "job_count": 6,
                "job_titles": [
                    "Senior ML Engineer",
                    "Data Scientist",
                    "Platform Engineer",
                    "Head of AI",
                ],
                "job_velocity_60d": 3,
            },
            "layoffs": {
                "timestamp": "2026-04-25T09:00:00+00:00",
                "source": "layoffs",
                "confidence": 0.3,
                "evidence": ["No layoffs detected for ExampleCo in available data."],
                "last_layoff_date": None,
                "total_layoffs_12m": 0,
                "severity_score": 0.0,
            },
            "leadership": {
                "timestamp": "2026-04-25T09:00:00+00:00",
                "source": "leadership",
                "confidence": 0.76,
                "evidence": ["Company appoints VP AI to lead generative AI roadmap."],
                "change_detected": True,
                "role_changed": "VP AI",
                "date": "2026-02-10",
            },
        },
    }

    result = compute_ai_maturity_score(sample_hiring_signal_brief)
    print("score:", result["score"])
    print("confidence:", result["confidence"])
    print("justification:", result["justification"])


if __name__ == "__main__":
    main()

