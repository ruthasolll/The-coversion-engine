from __future__ import annotations

import unittest

from agent.orchestrator import Orchestrator


class OrchestratorTests(unittest.TestCase):
    def test_build_plan(self) -> None:
        orchestrator = Orchestrator()
        plan = orchestrator.build_plan("Stripe")
        self.assertEqual(plan["company"], "Stripe")
        self.assertEqual(
            plan["steps"],
            ["fetch_crunchbase", "fetch_jobs", "fetch_layoffs", "check_leadership", "compute_ai_maturity"],
        )

    def test_run_collects_trace_and_confidence_updates(self) -> None:
        orchestrator = Orchestrator()
        orchestrator._step_fetchers = {  # type: ignore[attr-defined]
            "fetch_crunchbase": lambda _company: {
                "signal": "crunchbase_firmographics",
                "value": "known",
                "confidence": 0.8,
                "source": "https://www.crunchbase.com",
                "timestamp": "2026-04-25T00:00:00Z",
            },
            "fetch_jobs": lambda _company: {
                "signal": "job_post_velocity",
                "value": "known",
                "confidence": 0.7,
                "source": "https://example.com/jobs",
                "timestamp": "2026-04-25T00:00:00Z",
            },
            "fetch_layoffs": lambda _company: {
                "signal": "layoffs_fyi",
                "value": "known",
                "confidence": 0.6,
                "source": "data/raw/layoffs.csv",
                "timestamp": "2026-04-25T00:00:00Z",
            },
            "check_leadership": lambda _company: {
                "signal": "leadership_change_detection",
                "value": "known",
                "confidence": 0.5,
                "source": "https://duckduckgo.com",
                "timestamp": "2026-04-25T00:00:00Z",
            },
            "compute_ai_maturity": lambda _company: {
                "signal": "ai_maturity_scoring",
                "value": "known",
                "confidence": 0.9,
                "source": "heuristic_public_signals",
                "timestamp": "2026-04-25T00:00:00Z",
            },
        }
        state = orchestrator.run("Stripe")
        self.assertEqual(len(state.signals_collected), 5)
        self.assertEqual(len(state.run_trace), 5)
        self.assertEqual(len(state.intermediate_confidence_updates), 5)
        self.assertIn("crunchbase_firmographics", state.belief_state)
        self.assertIn("latency_ms", state.run_trace[0])

    def test_grounded_honesty_unknown_on_missing_fields(self) -> None:
        orchestrator = Orchestrator()
        orchestrator._step_fetchers = {step: (lambda _company: {"signal": "unknown_signal"}) for step in orchestrator.build_plan("A")["steps"]}  # type: ignore[attr-defined]
        state = orchestrator.run("A")
        first = state.signals_collected[0]
        self.assertEqual(first["value"], "unknown")
        self.assertEqual(first["source"], "unknown")
        self.assertEqual(first["confidence"], 0.1)


if __name__ == "__main__":
    unittest.main()
