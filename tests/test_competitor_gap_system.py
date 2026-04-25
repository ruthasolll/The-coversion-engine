from __future__ import annotations

import unittest

from enrichment.competitor_gap.pipeline import generate_competitor_gap_brief


class CompetitorGapSystemTests(unittest.TestCase):
    def test_pipeline_returns_brief_with_distribution_and_gaps(self) -> None:
        brief = generate_competitor_gap_brief(target_company_name="Example Company", sector="fintech")
        self.assertIn("competitors", brief)
        self.assertTrue(5 <= len(brief["competitors"]) <= 10 or brief.get("fallback_used"))
        self.assertIn("distribution", brief)
        self.assertIn("percentile", brief["distribution"])
        self.assertTrue(2 <= len(brief.get("gaps", [])) <= 3)
        self.assertEqual(len(brief["competitor_scores"]), len(brief["competitors"]))

    def test_sparse_sector_uses_fallback(self) -> None:
        brief = generate_competitor_gap_brief(target_company_name="Example Company", sector="unknown-niche-sector")
        self.assertIn("fallback_used", brief)
        self.assertIn("fallback_explanation", brief)


if __name__ == "__main__":
    unittest.main()

