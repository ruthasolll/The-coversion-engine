from __future__ import annotations

from typing import Any

from enrichment.competitor_gap.schema import CompetitiveGap


def _is_weak_signal(text: str) -> bool:
    """Heuristic for weak/absent signal language."""
    lowered = text.lower()
    weak_tokens = ("no ", "absent", "limited", "weak", "none", "does not", "not clearly")
    return any(token in lowered for token in weak_tokens)


def _is_strong_signal(text: str) -> bool:
    """Heuristic for strong signal language."""
    if _is_weak_signal(text):
        return False
    lowered = text.lower()
    strong_tokens = ("strong", "identified", "found", "active", "references", "dedicated")
    return any(token in lowered for token in strong_tokens)


def _gap_title_for_category(category: str) -> str:
    """Map scorer category to human-readable gap title."""
    mapping = {
        "ai_hiring": "AI Hiring Density Gap",
        "ai_leadership": "AI Leadership Gap",
        "github_activity": "Engineering Activity Visibility Gap",
        "executive_commentary": "Executive AI Narrative Gap",
        "ml_stack": "Modern ML Stack Signal Gap",
        "strategic_comm": "Strategic AI Communication Gap",
    }
    return mapping.get(category, "Competitive Signal Gap")


def extract_competitive_gaps(
    target_company: str,
    target_score: dict[str, Any],
    competitor_scores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract 2-3 evidence-backed competitive gaps."""
    if not competitor_scores:
        return []

    target_justification = target_score.get("justification", {})
    ordered = sorted(
        competitor_scores,
        key=lambda item: (-int(item.get("score", 0)), str(item.get("company", "")).lower()),
    )
    top_refs = ordered[:3]
    gaps: list[CompetitiveGap] = []

    for competitor in top_refs:
        comp_name = str(competitor.get("company", "competitor"))
        comp_summary = competitor.get("signals_summary", {})
        for category, comp_text in comp_summary.items():
            target_text = str(target_justification.get(category, ""))
            if _is_weak_signal(target_text) and _is_strong_signal(str(comp_text)):
                impact = "high" if int(competitor.get("score", 0)) - int(target_score.get("score", 0)) >= 2 else "medium"
                gap = CompetitiveGap(
                    gap_title=_gap_title_for_category(category),
                    description=(
                        f"{comp_name} shows stronger {category.replace('_', ' ')} indicators than {target_company}."
                    ),
                    evidence={
                        "competitor": comp_name,
                        "signal": str(comp_text),
                    },
                    competitor_reference=comp_name,
                    impact_level=impact,
                )
                gaps.append(gap)
            if len(gaps) >= 3:
                break
        if len(gaps) >= 3:
            break

    if len(gaps) < 2:
        lead_competitor = ordered[0]
        delta = int(lead_competitor.get("score", 0)) - int(target_score.get("score", 0))
        fallback_impact = "high" if delta >= 2 else "medium"
        gaps.append(
            CompetitiveGap(
                gap_title="Overall AI Maturity Position Gap",
                description=(
                    f"{lead_competitor.get('company')} scores higher on AI maturity versus {target_company}."
                ),
                evidence={
                    "competitor": str(lead_competitor.get("company")),
                    "signal": f"Competitor score={lead_competitor.get('score')} vs target score={target_score.get('score')}.",
                },
                competitor_reference=str(lead_competitor.get("company")),
                impact_level=fallback_impact,
            )
        )

    unique: list[CompetitiveGap] = []
    seen_titles: set[str] = set()
    for gap in gaps:
        key = f"{gap.gap_title}:{gap.competitor_reference}"
        if key in seen_titles:
            continue
        seen_titles.add(key)
        unique.append(gap)
    return [gap.asdict() for gap in unique[:3]]
