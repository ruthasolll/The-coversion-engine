from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from enrichment.hiring_signals.crunchbase_signal import fetch_crunchbase_signal
from enrichment.hiring_signals.jobs_signal import JobsSignal
from enrichment.hiring_signals.layoffs_signal import fetch_layoffs_signal
from enrichment.hiring_signals.leadership_signal import fetch_leadership_signal
from enrichment.hiring_signals.pipeline import run_hiring_signal_pipeline
from enrichment.hiring_signals.schema import CrunchbaseSignal, LayoffsSignal, LeadershipSignal


class HiringSignalsPipelineTests(unittest.TestCase):
    @patch("enrichment.hiring_signals.pipeline.fetch_leadership_signal")
    @patch("enrichment.hiring_signals.pipeline.fetch_layoffs_signal")
    @patch("enrichment.hiring_signals.pipeline.fetch_jobs_signal")
    @patch("enrichment.hiring_signals.pipeline.fetch_crunchbase_signal")
    def test_pipeline_output_shape(
        self,
        mock_crunchbase,
        mock_jobs,
        mock_layoffs,
        mock_leadership,
    ) -> None:
        mock_crunchbase.return_value = CrunchbaseSignal(
            timestamp="2026-04-25T00:00:00+00:00",
            source="crunchbase",
            confidence=0.9,
            evidence=["funding stage detected"],
            funding_stage="SERIES B",
            last_funding_date="2025-02-10",
            investors=["Alpha Capital"],
            funding_filter_passed=True,
        )
        mock_jobs.return_value = JobsSignal(
            timestamp="2026-04-25T00:00:00+00:00",
            source="jobs",
            confidence=0.7,
            evidence=["jobs scraped"],
            job_count=5,
            job_titles=["Senior Backend Engineer"],
            job_velocity_60d=2,
            baseline_job_count_60d=3,
        )
        mock_layoffs.return_value = LayoffsSignal(
            timestamp="2026-04-25T00:00:00+00:00",
            source="layoffs",
            confidence=0.4,
            evidence=["no layoffs detected"],
            last_layoff_date=None,
            total_layoffs_12m=0,
            severity_score=0.0,
        )
        mock_leadership.return_value = LeadershipSignal(
            timestamp="2026-04-25T00:00:00+00:00",
            source="leadership",
            confidence=0.5,
            evidence=["no change"],
            change_detected=False,
            role_changed=None,
            date=None,
        )

        result = run_hiring_signal_pipeline("Acme")
        self.assertEqual(result["company_name"], "Acme")
        self.assertIn("generated_at", result)
        self.assertIn("signals", result)
        self.assertIn("crunchbase", result["signals"])
        self.assertIn("jobs", result["signals"])
        self.assertIn("layoffs", result["signals"])
        self.assertIn("leadership", result["signals"])

    def test_crunchbase_missing_company_returns_zero_confidence(self) -> None:
        signal = fetch_crunchbase_signal("")
        self.assertEqual(signal.confidence, 0.0)
        self.assertEqual(signal.source, "crunchbase")

    def test_layoffs_no_history_returns_expected_edge_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "layoffs.csv"
            csv_path.write_text(
                "Company,Date,Laid_Off_Count\nOtherCo,2026-01-01,120\n",
                encoding="utf-8",
            )
            signal = fetch_layoffs_signal("Acme", csv_path=csv_path)
        self.assertEqual(signal.total_layoffs_12m, 0)
        self.assertEqual(signal.confidence, 0.3)
        self.assertIsNone(signal.last_layoff_date)

    @patch("enrichment.hiring_signals.leadership_signal._fetch_press_mentions")
    def test_leadership_no_change_edge_case(self, mock_press) -> None:
        mock_press.return_value = []
        signal = fetch_leadership_signal("Acme")
        self.assertFalse(signal.change_detected)
        self.assertEqual(signal.confidence, 0.5)


if __name__ == "__main__":
    unittest.main()

