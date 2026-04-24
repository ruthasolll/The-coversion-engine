from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from enrichment.merge_pipeline import build_enrichment_artifact, save_enrichment_artifact


class MergePipelineTests(unittest.TestCase):
    @patch("enrichment.merge_pipeline.estimate_ai_maturity")
    @patch("enrichment.merge_pipeline.fetch_leadership")
    @patch("enrichment.merge_pipeline.fetch_layoff_signals")
    @patch("enrichment.merge_pipeline.fetch_job_signals")
    @patch("enrichment.merge_pipeline.fetch_crunchbase")
    def test_build_and_save_artifact(
        self,
        mock_crunchbase,
        mock_jobs,
        mock_layoffs,
        mock_leadership,
        mock_ai,
    ) -> None:
        mock_crunchbase.return_value = {
            "signal": "crunchbase_firmographics",
            "value": "cb",
            "confidence": 0.8,
            "source": "a",
            "timestamp": "2026-04-25T00:00:00Z",
        }
        mock_jobs.return_value = {
            "signal": "job_post_velocity",
            "value": "jobs",
            "confidence": 0.7,
            "source": "b",
            "timestamp": "2026-04-25T00:00:00Z",
        }
        mock_layoffs.return_value = {
            "signal": "layoffs_fyi",
            "value": "none",
            "confidence": 0.6,
            "source": "c",
            "timestamp": "2026-04-25T00:00:00Z",
        }
        mock_leadership.return_value = {
            "signal": "leadership_change_detection",
            "value": "none",
            "confidence": 0.5,
            "source": "d",
            "timestamp": "2026-04-25T00:00:00Z",
        }
        mock_ai.return_value = {
            "signal": "ai_maturity_scoring",
            "value": "moderate",
            "confidence": 0.9,
            "source": "e",
            "timestamp": "2026-04-25T00:00:00Z",
        }

        artifact = build_enrichment_artifact(company="SavannaPay", jobs_url="https://example.com/jobs")
        self.assertEqual(artifact["company"], "SavannaPay")
        self.assertEqual(len(artifact["signals"]), 5)
        self.assertEqual(artifact["overall_confidence"], 0.7)

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "artifact.json"
            save_enrichment_artifact(artifact, output)
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved["overall_confidence"], 0.7)


if __name__ == "__main__":
    unittest.main()
