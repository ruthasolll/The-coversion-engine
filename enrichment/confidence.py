from __future__ import annotations


def confidence_from_score(score: float) -> float:
    return round(max(0.0, min(1.0, score)), 3)
