from __future__ import annotations

import unittest

from enrichment.ai_maturity.scorer import compute_ai_maturity_score


class AIMaturitySystemTests(unittest.TestCase):
    def test_returns_expected_shape_and_score_range(self) -> None:
        brief = {
            "company_name": "ExampleCo",
            "generated_at": "2026-04-25T09:00:00+00:00",
            "signals": {
                "crunchbase": {"evidence": ["Series A funding"], "investors": ["A"], "confidence": 0.8},
                "jobs": {"job_count": 3, "job_titles": ["ML Engineer", "Data Scientist"], "confidence": 0.8},
                "layoffs": {"evidence": ["No layoffs"], "confidence": 0.3},
                "leadership": {"evidence": ["New Head of AI appointed"], "role_changed": "Head of AI", "change_detected": True, "confidence": 0.8},
            },
        }
        result = compute_ai_maturity_score(brief)
        self.assertIn(result["score"], {0, 1, 2, 3})
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        self.assertIn("justification", result)
        self.assertEqual(
            set(result["justification"].keys()),
            {"ai_hiring", "ai_leadership", "github_activity", "executive_commentary", "ml_stack", "strategic_comm"},
        )

    def test_silent_company_case(self) -> None:
        result = compute_ai_maturity_score({"company_name": "SilentCo", "signals": {}})
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["confidence"], 0.1)
        self.assertIn("No public AI signals found", result["justification"]["ai_hiring"])


if __name__ == "__main__":
    unittest.main()

