from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from enrichment.ai_maturity.schema import AIMaturityResult, clamp_confidence, utc_now_iso
from enrichment.ai_maturity.weights import SCORE_SCALE, SIGNAL_WEIGHTS

AI_HIRING_KEYWORDS = (
    "ai",
    "ml",
    "machine learning",
    "data science",
    "data scientist",
    "ml engineer",
    "genai",
)
AI_LEADERSHIP_KEYWORDS = (
    "head of ai",
    "vp ai",
    "chief ai",
    "ml research lead",
    "cto",
)
ML_STACK_KEYWORDS = ("llm", "vector db", "transformers", "pytorch", "langchain")
STRATEGIC_COMM_KEYWORDS = (
    "ai strategy",
    "ai transformation",
    "investor update",
    "hiring announcement",
    "automation roadmap",
)


@dataclass
class SignalScore:
    """Internal score representation for one category."""

    value: float
    confidence: float
    found: str
    reason: str


def _normalize_hiring_signal_brief(hiring_signal_brief: Any) -> dict[str, Any]:
    """Normalize acceptable input forms into pipeline output dict shape."""
    if hasattr(hiring_signal_brief, "to_output"):
        output = hiring_signal_brief.to_output()
        if isinstance(output, dict):
            return output
    if isinstance(hiring_signal_brief, dict):
        if "signals" in hiring_signal_brief and isinstance(hiring_signal_brief["signals"], dict):
            return hiring_signal_brief
        keys = {"crunchbase_signal", "jobs_signal", "layoffs_signal", "leadership_signal"}
        if keys.issubset(set(hiring_signal_brief.keys())):
            return {
                "company_name": hiring_signal_brief.get("company_name", ""),
                "generated_at": hiring_signal_brief.get("generated_at", utc_now_iso()),
                "signals": {
                    "crunchbase": hiring_signal_brief.get("crunchbase_signal", {}),
                    "jobs": hiring_signal_brief.get("jobs_signal", {}),
                    "layoffs": hiring_signal_brief.get("layoffs_signal", {}),
                    "leadership": hiring_signal_brief.get("leadership_signal", {}),
                },
            }
    return {"company_name": "", "generated_at": utc_now_iso(), "signals": {}}


def _text_contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    """Case-insensitive keyword membership test."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _collect_text_blob(signals: dict[str, Any]) -> str:
    """Collect text blob from evidence fields for medium/low signal extraction."""
    parts: list[str] = []
    for signal in signals.values():
        evidence = signal.get("evidence", [])
        if isinstance(evidence, str):
            parts.append(evidence)
        elif isinstance(evidence, list):
            parts.extend(str(item) for item in evidence)
    return "\n".join(parts)


def _score_ai_hiring(jobs_signal: dict[str, Any]) -> SignalScore:
    """Score AI/ML hiring signal from job titles and counts."""
    titles = [str(title) for title in jobs_signal.get("job_titles", [])]
    ai_titles = [title for title in titles if _text_contains_any(title, AI_HIRING_KEYWORDS)]
    job_count = int(jobs_signal.get("job_count", 0) or 0)
    if ai_titles:
        strength = min(1.0, 0.5 + (0.1 * len(ai_titles)))
        return SignalScore(
            value=strength,
            confidence=0.9,
            found=f"Found {len(ai_titles)} AI/ML-oriented roles.",
            reason=f"AI hiring: Found {', '.join(ai_titles[:3])} -> strong signal of AI adoption.",
        )
    if job_count > 0:
        return SignalScore(
            value=0.35,
            confidence=0.55,
            found=f"Found {job_count} open roles, but none explicitly AI-focused.",
            reason="AI hiring: engineering recruitment exists but no explicit AI/ML role terms.",
        )
    return SignalScore(
        value=0.0,
        confidence=0.2,
        found="No open roles detected.",
        reason="AI hiring: no public hiring signal available.",
    )


def _score_ai_leadership(leadership_signal: dict[str, Any], jobs_signal: dict[str, Any]) -> SignalScore:
    """Score AI/ML leadership signal."""
    evidence_blob = _collect_text_blob({"leadership": leadership_signal})
    role_changed = str(leadership_signal.get("role_changed", "")).lower()
    titles = [str(title).lower() for title in jobs_signal.get("job_titles", [])]
    leadership_hits = [
        phrase
        for phrase in AI_LEADERSHIP_KEYWORDS
        if phrase in role_changed or phrase in evidence_blob.lower() or any(phrase in title for title in titles)
    ]
    if leadership_hits:
        return SignalScore(
            value=0.95,
            confidence=0.85,
            found=f"Leadership markers: {', '.join(sorted(set(leadership_hits)))}.",
            reason="AI leadership: dedicated or AI-adjacent executive signal identified.",
        )
    if leadership_signal.get("change_detected"):
        return SignalScore(
            value=0.4,
            confidence=0.6,
            found="Leadership change detected but not explicitly AI-focused.",
            reason="AI leadership: executive change may enable AI direction, but evidence is indirect.",
        )
    return SignalScore(
        value=0.0,
        confidence=0.5,
        found="No AI leadership signal detected.",
        reason="AI leadership: no explicit AI/ML executive role observed.",
    )


def _score_github_activity(jobs_signal: dict[str, Any], crunchbase_signal: dict[str, Any]) -> SignalScore:
    """Score GitHub activity using deterministic placeholder logic."""
    titles = [str(title).lower() for title in jobs_signal.get("job_titles", [])]
    engineering_titles = [title for title in titles if any(token in title for token in ("engineer", "developer", "platform"))]
    investors_count = len(crunchbase_signal.get("investors", []) or [])
    if engineering_titles:
        return SignalScore(
            value=0.75,
            confidence=0.65,
            found=f"Engineering role presence detected ({len(engineering_titles)} titles).",
            reason="GitHub activity proxy: active engineering hiring suggests repository activity.",
        )
    if investors_count > 0:
        return SignalScore(
            value=0.35,
            confidence=0.45,
            found="No engineering titles, but funded profile suggests build activity.",
            reason="GitHub activity proxy: indirect technical activity signal from funding context.",
        )
    return SignalScore(
        value=0.15,
        confidence=0.35,
        found="No direct engineering activity markers found.",
        reason="GitHub activity proxy: weak signal due to absent engineering markers.",
    )


def _score_executive_commentary(leadership_signal: dict[str, Any]) -> SignalScore:
    """Score executive AI commentary from leadership evidence text."""
    text_blob = _collect_text_blob({"leadership": leadership_signal}).lower()
    ai_terms = ("ai", "machine learning", "llm", "generative", "automation")
    hits = [term for term in ai_terms if term in text_blob]
    if hits:
        return SignalScore(
            value=0.8,
            confidence=0.7,
            found=f"Executive commentary includes terms: {', '.join(sorted(set(hits)))}.",
            reason="Executive commentary: leadership discourse references AI themes.",
        )
    return SignalScore(
        value=0.2,
        confidence=0.4,
        found="No explicit AI commentary terms found in leadership evidence.",
        reason="Executive commentary: public narrative does not clearly mention AI.",
    )


def _score_ml_stack(jobs_signal: dict[str, Any], leadership_signal: dict[str, Any]) -> SignalScore:
    """Score modern ML stack adoption signal from keywords."""
    combined = "\n".join(
        [str(item) for item in jobs_signal.get("job_titles", [])]
        + [str(item) for item in leadership_signal.get("evidence", [])]
    )
    matches = [keyword for keyword in ML_STACK_KEYWORDS if keyword in combined.lower()]
    if matches:
        return SignalScore(
            value=0.75,
            confidence=0.65,
            found=f"Stack keywords detected: {', '.join(sorted(set(matches)))}.",
            reason="Modern stack: references indicate probable contemporary ML tooling use.",
        )
    return SignalScore(
        value=0.1,
        confidence=0.3,
        found="No modern ML stack keywords detected.",
        reason="Modern stack: absent public references to common ML platform/tool terms.",
    )


def _score_strategic_comm(signals: dict[str, Any]) -> SignalScore:
    """Score strategic communication from all available evidence."""
    blob = _collect_text_blob(signals).lower()
    matches = [keyword for keyword in STRATEGIC_COMM_KEYWORDS if keyword in blob]
    if matches:
        return SignalScore(
            value=0.7,
            confidence=0.6,
            found=f"Strategic communication keywords: {', '.join(sorted(set(matches)))}.",
            reason="Strategic communication: messaging suggests AI direction at company level.",
        )
    return SignalScore(
        value=0.15,
        confidence=0.35,
        found="No clear strategic AI communication keywords found.",
        reason="Strategic communication: limited evidence of explicit AI transformation narrative.",
    )


def _to_score_bucket(weighted_scaled_score: float) -> int:
    """Map scaled weighted score to required 0..3 bucket."""
    if weighted_scaled_score < 0.4:
        return 0
    if weighted_scaled_score < 1.2:
        return 1
    if weighted_scaled_score < 2.0:
        return 2
    return 3


def compute_ai_maturity_score(hiring_signal_brief: Any) -> dict[str, Any]:
    """Compute AI maturity score (0..3) from HiringSignalBrief structured input."""
    normalized = _normalize_hiring_signal_brief(hiring_signal_brief)
    signals = normalized.get("signals", {})
    crunchbase = signals.get("crunchbase", {}) if isinstance(signals, dict) else {}
    jobs = signals.get("jobs", {}) if isinstance(signals, dict) else {}
    layoffs = signals.get("layoffs", {}) if isinstance(signals, dict) else {}
    leadership = signals.get("leadership", {}) if isinstance(signals, dict) else {}

    if not signals:
        silent_result = AIMaturityResult(
            score=0,
            confidence=0.1,
            justification={
                "ai_hiring": "No public AI signals found. Absence does not imply lack of capability.",
                "ai_leadership": "No public AI signals found. Absence does not imply lack of capability.",
                "github_activity": "No public AI signals found. Absence does not imply lack of capability.",
                "executive_commentary": "No public AI signals found. Absence does not imply lack of capability.",
                "ml_stack": "No public AI signals found. Absence does not imply lack of capability.",
                "strategic_comm": "No public AI signals found. Absence does not imply lack of capability.",
            },
            evidence_summary=["No public AI signals found. Absence does not imply lack of capability."],
            timestamp=utc_now_iso(),
        )
        return silent_result.to_dict()

    category_scores: dict[str, SignalScore] = {
        "ai_hiring": _score_ai_hiring(jobs),
        "ai_leadership": _score_ai_leadership(leadership, jobs),
        "github_activity": _score_github_activity(jobs, crunchbase),
        "executive_commentary": _score_executive_commentary(leadership),
        "ml_stack": _score_ml_stack(jobs, leadership),
        "strategic_comm": _score_strategic_comm(
            {"crunchbase": crunchbase, "jobs": jobs, "layoffs": layoffs, "leadership": leadership}
        ),
    }

    weighted_sum = sum(
        category_scores[name].value * weight for name, weight in SIGNAL_WEIGHTS.items()
    )
    scaled_score = weighted_sum * SCORE_SCALE
    final_score = _to_score_bucket(scaled_score)

    confidence_components = [score.confidence for score in category_scores.values()]
    overall_confidence = clamp_confidence(sum(confidence_components) / len(confidence_components))

    justification = {
        name: (
            f"{score.reason} "
            f"Found: {score.found} "
            f"Signal confidence={score.confidence:.2f}, weighted contribution={score.value * SIGNAL_WEIGHTS[name]:.2f}."
        )
        for name, score in category_scores.items()
    }

    evidence_summary = [
        f"{name}: {category_scores[name].found}" for name in SIGNAL_WEIGHTS.keys()
    ]
    evidence_summary.append(f"Scaled weighted score={scaled_score:.2f} -> maturity bucket {final_score}.")

    result = AIMaturityResult(
        score=final_score,
        confidence=overall_confidence,
        justification=justification,
        evidence_summary=evidence_summary,
        timestamp=utc_now_iso(),
    )
    return result.to_dict()

