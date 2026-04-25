from __future__ import annotations

from typing import Any

from enrichment.competitor_gap.schema import CompetitiveGap

GAP_CATEGORIES = [
    "ai_hiring",
    "ai_leadership",
    "ml_stack",
    "github_activity",
    "strategic_comm",
]


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
    candidates: list[dict[str, Any]] = []
    seen_categories: set[str] = set()

    for competitor in ordered:
        comp_name = str(competitor.get("company", "competitor"))
        comp_summary = competitor.get("signals_summary", {})
        delta = int(competitor.get("score", 0)) - int(target_score.get("score", 0))
        for category in GAP_CATEGORIES:
            if category in seen_categories:
                continue
            comp_text = str(comp_summary.get(category, "")).strip()
            if not comp_text:
                continue
            target_text = str(target_justification.get(category, ""))
            if _is_weak_signal(target_text) and _is_strong_signal(str(comp_text)):
                impact = "high" if delta >= 2 else "medium"
                candidates.append(
                    {
                        "category": category,
                        "company": comp_name,
                        "signal": comp_text,
                        "delta": delta,
                        "impact": impact,
                    }
                )
                seen_categories.add(category)
            if len(seen_categories) >= 3:
                break
        if len(seen_categories) >= 3:
            break

    if len(candidates) < 2:
        lead_competitor = ordered[0]
        lead_summary = lead_competitor.get("signals_summary", {})
        delta = int(lead_competitor.get("score", 0)) - int(target_score.get("score", 0))
        for category in GAP_CATEGORIES:
            if any(item["category"] == category for item in candidates):
                continue
            signal_text = str(lead_summary.get(category, "")).strip()
            if not signal_text:
                continue
            candidates.append(
                {
                    "category": category,
                    "company": str(lead_competitor.get("company", "competitor")),
                    "signal": signal_text,
                    "delta": delta,
                    "impact": "high" if delta >= 2 else "medium",
                }
            )
            if len(candidates) >= 2:
                break

    ranked = sorted(
        candidates,
        key=lambda item: (-int(item["delta"]), GAP_CATEGORIES.index(item["category"])),
    )

    selected: list[CompetitiveGap] = []
    selected_categories: set[str] = set()
    for item in ranked:
        category = str(item["category"])
        if category in selected_categories:
            continue
        selected_categories.add(category)
        selected.append(
            CompetitiveGap(
                gap_title=_gap_title_for_category(category),
                description=(
                    f"{item['company']} shows stronger {category.replace('_', ' ')} indicators than {target_company}."
                ),
                evidence={"competitor": str(item["company"]), "signal": str(item["signal"])},
                competitor_reference=str(item["company"]),
                impact_level=str(item["impact"]),
            )
        )
        if len(selected) == 3:
            break

    return [gap.asdict() for gap in selected[:3]]
