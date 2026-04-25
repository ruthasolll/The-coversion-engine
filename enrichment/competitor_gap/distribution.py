from __future__ import annotations

from typing import Any

from enrichment.competitor_gap.schema import DistributionPosition


def compute_distribution_position(target_score: int, competitor_scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute percentile/rank/above_count with deterministic tie handling."""
    ordered = sorted(
        competitor_scores,
        key=lambda item: (-int(item.get("score", 0)), str(item.get("company", "")).lower()),
    )
    total = len(ordered) + 1
    above_count = sum(1 for item in ordered if int(item.get("score", 0)) > int(target_score))
    rank = above_count + 1
    percentile = ((total - rank) / max(1, total - 1)) * 100.0
    distribution = DistributionPosition(
        percentile=percentile,
        rank=rank,
        total_competitors=total - 1,
        above_count=above_count,
    )
    return distribution.asdict()

