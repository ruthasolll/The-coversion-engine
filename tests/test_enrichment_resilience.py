from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from enrichment.tenacious.crunchbase import _slug, fetch_crunchbase
from enrichment.tenacious.jobs import fetch_job_signals


class EnrichmentResilienceTests(unittest.TestCase):
    def test_slug_generation_is_safe_and_deterministic(self) -> None:
        self.assertEqual(_slug("  Stripe  "), "stripe")
        self.assertEqual(_slug("ACME, Inc."), "acme-inc")
        self.assertEqual(_slug("  _Hello__World_  "), "hello-world")

    @patch("enrichment.tenacious.crunchbase.requests.get")
    def test_crunchbase_403_returns_structured_fallback(self, mock_get: Mock) -> None:
        response = Mock()
        response.ok = False
        response.status_code = 403
        response.text = ""
        mock_get.return_value = response

        signal = fetch_crunchbase("Stripe")
        self.assertEqual(signal["signal"], "crunchbase_firmographics")
        self.assertIn("anti-bot protection", signal["value"])
        self.assertEqual(signal["confidence"], 0.4)
        self.assertIn("/organization/stripe", signal["source"])

    @patch("enrichment.tenacious.crunchbase.requests.get", side_effect=RuntimeError("network broke"))
    def test_crunchbase_exception_returns_low_confidence_signal(self, _mock_get: Mock) -> None:
        signal = fetch_crunchbase("Stripe")
        self.assertEqual(signal["signal"], "crunchbase_firmographics")
        self.assertIn("Crunchbase fetch failed", signal["value"])
        self.assertEqual(signal["confidence"], 0.1)

    @patch("enrichment.tenacious.jobs.sync_playwright", side_effect=RuntimeError("playwright unavailable"))
    def test_jobs_exception_returns_structured_fallback(self, _mock_playwright: Mock) -> None:
        signal = fetch_job_signals("https://example.com/jobs")
        self.assertEqual(signal["signal"], "job_post_velocity")
        self.assertIn("Jobs fetch failed", signal["value"])
        self.assertEqual(signal["confidence"], 0.1)


if __name__ == "__main__":
    unittest.main()
