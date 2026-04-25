from __future__ import annotations

from typing import Any

from enrichment.competitor_gap.schema import DistributionPosition


def _normalize_competitor_scores(competitor_scores: list[Any]) -> list[int]:
    """Normalize competitor scores to integer list."""
    normalized: list[int] = []
    for item in competitor_scores:
        if isinstance(item, dict):
            normalized.append(int(item.get("score", 0)))
        else:
            normalized.append(int(item))
    return normalized


def compute_distribution_position(target_score: int, competitor_scores: list[Any]) -> dict[str, Any]:
    """Compute percentile/rank/above_count with deterministic tie handling."""
    scores = _normalize_competitor_scores(competitor_scores)
    all_scores = scores + [int(target_score)]
    sorted_scores = sorted(all_scores, reverse=True)
    rank = sorted_scores.index(int(target_score)) + 1

    total = len(scores)
    above_count = sum(1 for score in scores if score > int(target_score))
    below_count = sum(1 for score in scores if score < int(target_score))
    percentile = 0.0 if total == 0 else (below_count / total) * 100.0
    percentile = max(0.0, min(100.0, percentile))

    distribution = DistributionPosition(
        percentile=percentile,
        rank=rank,
        total_competitors=total,
        above_count=above_count,
    )
    return distribution.asdict()
