from __future__ import annotations

from typing import Any

from enrichment.ai_maturity.scorer import compute_ai_maturity_score


def run_ai_maturity_pipeline(hiring_signal_brief: Any) -> dict:
    """Optional orchestrator wrapper for AI maturity scoring."""
    return compute_ai_maturity_score(hiring_signal_brief)

