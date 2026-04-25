from __future__ import annotations

from typing import Any

from enrichment.competitor_gap.distribution import compute_distribution_position
from enrichment.competitor_gap.gap_extractor import extract_competitive_gaps
from enrichment.competitor_gap.schema import (
    CompetitiveGap,
    CompetitorGapBrief,
    CompetitorScore,
    DistributionPosition,
    utc_now_iso,
)
from enrichment.competitor_gap.scorer_adapter import score_company, score_competitors
from enrichment.competitor_gap.selector import infer_sector, select_competitors


def _build_competitor_score_objects(competitor_scores: list[dict[str, Any]]) -> list[CompetitorScore]:
    """Convert raw score payloads to schema objects."""
    return [
        CompetitorScore(
            company=str(item.get("company")),
            score=int(item.get("score", 0)),
            confidence=float(item.get("confidence", 0.0)),
            signals_summary=dict(item.get("signals_summary", {})),
        )
        for item in competitor_scores
    ]


def _compute_brief_confidence(target_score: dict[str, Any], competitor_scores: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> float:
    """Compute aggregate brief confidence."""
    confidences = [float(target_score.get("confidence", 0.0))]
    confidences.extend(float(item.get("confidence", 0.0)) for item in competitor_scores)
    base = sum(confidences) / max(1, len(confidences))
    gap_bonus = 0.05 if len(gaps) >= 2 else 0.0
    return max(0.0, min(1.0, round(base + gap_bonus, 2)))


def _build_gap_objects(gaps: list[dict[str, Any]]) -> list[CompetitiveGap]:
    """Convert extracted gaps into schema objects."""
    return [
        CompetitiveGap(
            gap_title=str(item.get("gap_title", "Competitive Signal Gap")),
            description=str(item.get("description", "")),
            evidence=dict(item.get("evidence", {})),
            competitor_reference=str(item.get("competitor_reference", "")),
            impact_level=str(item.get("impact_level", "medium")),
        )
        for item in gaps[:3]
    ]


def generate_competitor_gap_brief(
    target_company_name: str,
    sector: str | None = None,
    target_hiring_signal_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate structured competitor gap brief for a target company."""
    target_hiring_signal_brief = target_hiring_signal_brief or {
        "company_name": target_company_name,
        "generated_at": utc_now_iso(),
        "signals": {},
    }
    inferred_sector = infer_sector(
        company_name=target_company_name,
        sector=sector,
        crunchbase_signal=target_hiring_signal_brief.get("signals", {}).get("crunchbase", {}),
    )
    competitors, fallback_used, fallback_explanation = select_competitors(
        company_name=target_company_name,
        sector=inferred_sector,
    )

    target_score = score_company(
        company=target_company_name,
        sector=inferred_sector,
        hiring_signal_brief=target_hiring_signal_brief,
    )["full_result"]

    competitor_scores_raw = score_competitors(competitors=competitors, sector=inferred_sector)
    distribution_raw = compute_distribution_position(
        target_score=int(target_score.get("score", 0)),
        competitor_scores=competitor_scores_raw,
    )
    gaps = extract_competitive_gaps(
        target_company=target_company_name,
        target_score=target_score,
        competitor_scores=competitor_scores_raw,
    )
    confidence_score = _compute_brief_confidence(
        target_score=target_score,
        competitor_scores=competitor_scores_raw,
        gaps=gaps,
    )

    brief = CompetitorGapBrief(
        target_company=target_company_name,
        sector=inferred_sector,
        generated_at=utc_now_iso(),
        competitors=competitors,
        target_score=target_score,
        competitor_scores=_build_competitor_score_objects(competitor_scores_raw),
        distribution=DistributionPosition(
            percentile=float(distribution_raw.get("percentile", 0.0)),
            rank=int(distribution_raw.get("rank", 1)),
            total_competitors=int(distribution_raw.get("total_competitors", len(competitors))),
            above_count=int(distribution_raw.get("above_count", 0)),
        ),
        gaps=_build_gap_objects(gaps),
        confidence_score=confidence_score,
        fallback_used=fallback_used,
        fallback_explanation=fallback_explanation,
    )
    return brief.to_dict()
