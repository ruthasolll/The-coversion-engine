from __future__ import annotations

import logging
from datetime import datetime, timezone

from agent.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

_WEIGHTS = {
    "crunchbase_firmographics": 0.25,
    "job_post_velocity": 0.25,
    "layoffs_fyi": 0.2,
    "leadership_change_detection": 0.15,
    "ai_maturity_scoring": 0.15,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_signal(signal: dict, fallback_signal_name: str, fallback_source: str) -> dict:
    if not isinstance(signal, dict):
        raise ValueError("signal must be a dict")
    confidence = signal.get("confidence", 0.1)
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        confidence_value = 0.1

    return {
        "signal": str(signal.get("signal") or fallback_signal_name),
        "value": str(signal.get("value") or f"{fallback_signal_name} produced no value"),
        "confidence": round(max(0.0, min(1.0, confidence_value)), 2),
        "source": str(signal.get("source") or fallback_source),
        "timestamp": str(signal.get("timestamp") or _utc_now()),
    }


def _signal_confidence(signals: list[dict], name: str) -> float:
    for signal in signals:
        if signal.get("signal") == name:
            try:
                return float(signal.get("confidence", 0.0))
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _signal_value(signals: list[dict], name: str) -> str:
    for signal in signals:
        if signal.get("signal") == name:
            return str(signal.get("value", ""))
    return ""


def _derive_reasoning_inputs(signals: list[dict]) -> tuple[float, float, float, float]:
    hiring_confidence = _signal_confidence(signals, "job_post_velocity")
    layoffs_raw = _signal_confidence(signals, "layoffs_fyi")
    layoffs_value = _signal_value(signals, "layoffs_fyi").lower()
    ai_maturity_confidence = _signal_confidence(signals, "ai_maturity_scoring")
    leadership_value = _signal_value(signals, "leadership_change_detection").lower()

    if "layoff record found" in layoffs_value:
        layoffs_confidence = layoffs_raw
    elif "no layoffs.fyi record found" in layoffs_value:
        layoffs_confidence = 0.2
    elif "unavailable" in layoffs_value or "failed" in layoffs_value:
        layoffs_confidence = 0.5
    else:
        layoffs_confidence = max(0.3, min(0.6, 1 - layoffs_raw))

    if "no public leadership-change signal found" in leadership_value:
        leadership_stability = 0.8
    elif "failed" in leadership_value:
        leadership_stability = 0.4
    else:
        leadership_stability = 0.5

    return (
        round(hiring_confidence, 2),
        round(layoffs_confidence, 2),
        round(ai_maturity_confidence, 2),
        round(leadership_stability, 2),
    )


def _dominant_weighted_signals(signals: list[dict]) -> str:
    ranked: list[tuple[str, float]] = []
    for signal in signals:
        name = str(signal.get("signal", ""))
        if name not in _WEIGHTS:
            continue
        contribution = float(signal.get("confidence", 0.0)) * _WEIGHTS[name]
        ranked.append((name, contribution))
    ranked.sort(key=lambda item: item[1], reverse=True)
    top = [f"{name}={round(score, 3)}" for name, score in ranked[:2]]
    return ", ".join(top) if top else "none"


def _fusion_summary(signals: list[dict]) -> str:
    (
        hiring_confidence,
        layoffs_confidence,
        ai_maturity_confidence,
        leadership_stability,
    ) = _derive_reasoning_inputs(signals)

    if hiring_confidence > 0.75 and layoffs_confidence < 0.3:
        summary = "Strong expansion phase with aggressive hiring and low restructuring signals"
    elif layoffs_confidence > 0.7:
        summary = "Potential restructuring or cost optimization phase"
    elif ai_maturity_confidence > 0.7:
        summary = "Strong AI adoption and technical innovation signals"
    else:
        summary = "Mixed signals with moderate growth indicators"

    if summary.startswith("Strong expansion phase") and leadership_stability >= 0.65:
        summary = f"{summary}; leadership appears stable"
    elif summary.startswith("Potential restructuring") and leadership_stability < 0.5:
        summary = f"{summary}; leadership volatility may amplify execution risk"

    dominant = _dominant_weighted_signals(signals)
    return (
        f"{summary}. "
        f"Reasoning: hiring_confidence={hiring_confidence}, "
        f"layoffs_confidence={layoffs_confidence}, "
        f"ai_maturity_confidence={ai_maturity_confidence}, "
        f"leadership_stability={leadership_stability}. "
        f"Dominant weighted signals: {dominant}."
    )


def _risk_score(signals: list[dict]) -> tuple[float, str]:
    layoffs_text = next((s.get("value", "").lower() for s in signals if s.get("signal") == "layoffs_fyi"), "")
    leadership_text = next((s.get("value", "").lower() for s in signals if s.get("signal") == "leadership_change_detection"), "")
    score = 0.2
    reasons = ["base risk floor (0.20) for incomplete external certainty"]
    if "layoff record found" in layoffs_text:
        score += 0.45
        reasons.append("layoff record detected (+0.45)")
    elif "no layoffs.fyi record found" in layoffs_text:
        reasons.append("no layoff record detected (+0.00)")
    else:
        reasons.append("layoff clarity reduced (treated as neutral)")
    if "top leadership-change result" in leadership_text:
        score += 0.2
        reasons.append("leadership transition signal detected (+0.20)")
    elif "no public leadership-change signal found" in leadership_text:
        reasons.append("leadership appears stable (+0.00)")
    else:
        reasons.append("leadership uncertainty present")
    return round(min(1.0, score), 2), "; ".join(reasons)


def _opportunity_score(signals: list[dict]) -> tuple[float, str]:
    jobs_conf = float(next((s.get("confidence", 0.0) for s in signals if s.get("signal") == "job_post_velocity"), 0.0))
    ai_conf = float(next((s.get("confidence", 0.0) for s in signals if s.get("signal") == "ai_maturity_scoring"), 0.0))
    layoffs_text = next((s.get("value", "").lower() for s in signals if s.get("signal") == "layoffs_fyi"), "")
    score = (jobs_conf * 0.5) + (ai_conf * 0.5)
    reasons = [f"hiring confidence contribution={round(jobs_conf * 0.5, 2)}", f"AI maturity contribution={round(ai_conf * 0.5, 2)}"]
    if "layoff record found" in layoffs_text:
        score -= 0.2
        reasons.append("active layoff signal penalty (-0.20)")
    elif "no layoffs.fyi record found" in layoffs_text:
        reasons.append("no layoff penalty applied")
    else:
        reasons.append("layoff signal unclear; no explicit penalty")
    return round(max(0.0, min(1.0, score)), 2), "; ".join(reasons)


def _executive_narrative(signals: list[dict], base_summary: str, risk_score: float, opportunity_score: float) -> str:
    (
        hiring_confidence,
        layoffs_confidence,
        ai_maturity_confidence,
        leadership_stability,
    ) = _derive_reasoning_inputs(signals)
    contradiction = hiring_confidence >= 0.7 and layoffs_confidence >= 0.7

    if contradiction:
        context = (
            "Contradictory momentum is present: hiring and restructuring signals are both elevated, "
            "which can indicate selective growth during cost optimization."
        )
    elif risk_score > 0.7 and opportunity_score < 0.45:
        context = "Near-term execution risk outweighs upside; prioritize account qualification and timeline sensitivity."
    elif opportunity_score > 0.65 and risk_score < 0.45:
        context = "Commercial timing is favorable; expansion indicators are stronger than restructuring pressure."
    else:
        context = "The account shows mixed directional evidence and benefits from staged outreach with re-verification."

    if leadership_stability >= 0.7:
        leadership_note = "Leadership appears stable, reducing change-management drag."
    elif leadership_stability <= 0.45:
        leadership_note = "Leadership volatility could slow decisions despite positive pockets of demand."
    else:
        leadership_note = "Leadership posture is neutral based on current public evidence."

    ai_note = (
        "AI adoption readiness is high and may accelerate technical buyer engagement."
        if ai_maturity_confidence > 0.7
        else "AI adoption signal is moderate; message should balance innovation with operational proof."
    )
    return f"{base_summary} {context} {leadership_note} {ai_note}"


def run_fusion_enrichment(company: str) -> dict:
    company_name = company.strip()
    orchestrator = Orchestrator()
    run_state = orchestrator.run(company_name)
    signals = [
        _normalize_signal(signal=s, fallback_signal_name="source_failure", fallback_source="unknown")
        for s in run_state.signals_collected
    ]

    overall_confidence = round(
        sum(float(signal["confidence"]) * _WEIGHTS.get(str(signal["signal"]), 0.0) for signal in signals),
        3,
    )
    risk_score, risk_reasoning = _risk_score(signals)
    opportunity_score, opportunity_reasoning = _opportunity_score(signals)
    base_summary = _fusion_summary(signals)
    artifact = {
        "company": company_name,
        "signals": signals,
        "fusion_summary": _executive_narrative(
            signals=signals,
            base_summary=base_summary,
            risk_score=risk_score,
            opportunity_score=opportunity_score,
        ),
        "overall_confidence": overall_confidence,
        "risk_score": risk_score,
        "opportunity_score": opportunity_score,
        "risk_reasoning": risk_reasoning,
        "opportunity_reasoning": opportunity_reasoning,
        "plan": run_state.plan,
        "belief_state": run_state.belief_state,
        "intermediate_confidence_updates": run_state.intermediate_confidence_updates,
        "run_trace": run_state.run_trace,
        "timestamp": _utc_now(),
    }
    logger.info(
        "fusion_event",
        extra={
            "company": company_name,
            "signals_count": len(signals),
            "overall_confidence": artifact["overall_confidence"],
        },
    )
    return artifact
