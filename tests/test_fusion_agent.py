from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.orchestrator import RunState
from enrichment.tenacious.fusion_agent import run_fusion_enrichment


class FusionAgentTests(unittest.TestCase):
    def _make_run_state(self) -> RunState:
        state = RunState(company="Acme")
        state.plan = {
            "company": "Acme",
            "steps": [
                "fetch_crunchbase",
                "fetch_jobs",
                "fetch_layoffs",
                "check_leadership",
                "compute_ai_maturity",
            ],
        }
        state.signals_collected = [
            {
                "signal": "crunchbase_firmographics",
                "value": "cb",
                "confidence": 0.8,
                "source": "cb",
                "timestamp": "2026-04-25T00:00:00Z",
            },
            {
                "signal": "job_post_velocity",
                "value": "jobs",
                "confidence": 0.6,
                "source": "jobs",
                "timestamp": "2026-04-25T00:00:00Z",
            },
            {
                "signal": "layoffs_fyi",
                "value": "none",
                "confidence": 0.4,
                "source": "layoffs",
                "timestamp": "2026-04-25T00:00:00Z",
            },
            {
                "signal": "leadership_change_detection",
                "value": "none",
                "confidence": 0.5,
                "source": "leadership",
                "timestamp": "2026-04-25T00:00:00Z",
            },
            {
                "signal": "ai_maturity_scoring",
                "value": "moderate",
                "confidence": 0.9,
                "source": "ai",
                "timestamp": "2026-04-25T00:00:00Z",
            },
        ]
        state.belief_state = {"job_post_velocity": {"value": "jobs", "confidence": 0.6, "source": "jobs"}}
        state.intermediate_confidence_updates = [
            {"step": "fetch_crunchbase", "signal": "crunchbase_firmographics", "confidence": 0.8, "running_confidence": 0.8}
        ]
        state.run_trace = [
            {
                "step": "fetch_crunchbase",
                "start_time": "2026-04-25T00:00:00Z",
                "end_time": "2026-04-25T00:00:01Z",
                "latency_ms": 1000.0,
                "success": True,
                "failure": None,
                "signal": "crunchbase_firmographics",
                "confidence": 0.8,
            }
        ]
        return state

    @patch("enrichment.tenacious.fusion_agent.Orchestrator.run")
    def test_run_fusion_enrichment_weighted_output(self, mock_run) -> None:
        mock_run.return_value = self._make_run_state()

        artifact = run_fusion_enrichment("Acme")
        self.assertEqual(artifact["company"], "Acme")
        self.assertEqual(len(artifact["signals"]), 5)
        self.assertAlmostEqual(artifact["overall_confidence"], 0.64, places=3)
        self.assertIn("fusion_summary", artifact)
        self.assertIn("Strong AI adoption and technical innovation signals", artifact["fusion_summary"])
        self.assertIn("Reasoning:", artifact["fusion_summary"])
        self.assertIn("Dominant weighted signals:", artifact["fusion_summary"])
        self.assertIn("risk_reasoning", artifact)
        self.assertIn("opportunity_reasoning", artifact)
        self.assertIn("hiring confidence contribution", artifact["opportunity_reasoning"])
        self.assertIn("risk_score", artifact)
        self.assertIn("opportunity_score", artifact)
        self.assertIn("run_trace", artifact)
        self.assertIn("plan", artifact)
        self.assertIn("belief_state", artifact)
        self.assertIn("intermediate_confidence_updates", artifact)
        self.assertIn("timestamp", artifact)

    @patch("enrichment.tenacious.fusion_agent.Orchestrator.run")
    def test_run_fusion_enrichment_source_failure_fallback(self, mock_run) -> None:
        state = self._make_run_state()
        state.signals_collected[1] = {
            "signal": "source_failure",
            "value": "fetch_jobs failed: boom",
            "confidence": 0.1,
            "source": "unknown",
            "timestamp": "2026-04-25T00:00:00Z",
        }
        mock_run.return_value = state

        artifact = run_fusion_enrichment("Acme")
        jobs_signal = next(s for s in artifact["signals"] if s["signal"] == "source_failure")
        self.assertIn("fetch_jobs failed", jobs_signal["value"])
        self.assertEqual(jobs_signal["confidence"], 0.1)


if __name__ == "__main__":
    unittest.main()
