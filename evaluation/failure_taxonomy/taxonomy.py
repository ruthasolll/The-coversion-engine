from __future__ import annotations

from evaluation.adversarial_probes.categories import CATEGORIES
from evaluation.failure_taxonomy.aggregator import compute_average_trigger_rate

PATTERN_DESCRIPTIONS = {
    "icp_misclassification": "System incorrectly classifies company segment, causing misaligned targeting and poor-fit outreach.",
    "hiring_signal_overclaim": "System extrapolates weak hiring evidence into strong intent claims that prospects dispute.",
    "bench_overcommitment": "System over-promises talent readiness or fit beyond actual bench capacity, increasing deal-break risk.",
    "tone_drift": "Outbound messaging style drifts from stakeholder expectations, reducing trust and response quality.",
    "multi_thread_leakage": "Signals or context from one account leak into another thread, creating factual and confidentiality errors.",
    "cost_pathology": "Execution path triggers unnecessary compute or human effort on low-value opportunities.",
    "dual_control_coordination": "Independent control gates resolve inconsistently, producing contradictory operational outcomes.",
    "scheduling_edge_cases": "Scheduling automation fails on timezone, replay, or availability edge cases.",
    "signal_reliability": "Underlying public signals are stale, ambiguous, or noisy and lead to fragile inferences.",
    "gap_overclaiming": "Competitive gap narratives overstate certainty or severity relative to available evidence.",
}


def build_failure_taxonomy(probes: list[dict]) -> dict:
    """Build category-level failure taxonomy from adversarial probes."""
    grouped: dict[str, list[dict]] = {category: [] for category in CATEGORIES}
    for probe in probes:
        category = str(probe["category"])
        if category not in grouped:
            raise ValueError(f"Unexpected category found in probes: {category}")
        grouped[category].append(probe)

    categories_payload: dict[str, dict] = {}
    for category in CATEGORIES:
        category_probes = grouped[category]
        categories_payload[category] = {
            "probe_count": len(category_probes),
            "aggregate_trigger_rate": compute_average_trigger_rate(category_probes),
            "pattern_description": PATTERN_DESCRIPTIONS[category],
            "probe_ids": [str(item["probe_id"]) for item in category_probes],
        }

    return {"categories": categories_payload}

