from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """Return current UTC timestamp as ISO-8601."""
    return datetime.now(timezone.utc).isoformat()


def clamp_confidence(value: float) -> float:
    """Clamp confidence score to 0..1 inclusive."""
    return max(0.0, min(1.0, round(float(value), 2)))


@dataclass
class CompetitorScore:
    """Per-competitor AI maturity scoring output."""

    company: str
    score: int
    confidence: float
    signals_summary: dict[str, str]

    def asdict(self) -> dict[str, Any]:
        """Serialize competitor score safely."""
        payload = asdict(self)
        payload["score"] = int(max(0, min(3, self.score)))
        payload["confidence"] = clamp_confidence(self.confidence)
        return payload


@dataclass
class DistributionPosition:
    """Target positioning against competitor score distribution."""

    percentile: float
    rank: int
    total_competitors: int
    above_count: int

    def asdict(self) -> dict[str, Any]:
        """Serialize distribution payload."""
        payload = asdict(self)
        payload["percentile"] = round(float(self.percentile), 2)
        return payload


@dataclass
class CompetitiveGap:
    """Evidence-backed actionable competitive gap."""

    gap_title: str
    description: str
    evidence: dict[str, str]
    competitor_reference: str
    impact_level: str

    def asdict(self) -> dict[str, Any]:
        """Serialize gap payload."""
        payload = asdict(self)
        impact = str(self.impact_level).strip().lower()
        payload["impact_level"] = impact if impact in {"low", "medium", "high"} else "medium"
        return payload


@dataclass
class CompetitorGapBrief:
    """Top-level competitor gap brief schema."""

    target_company: str
    sector: str
    generated_at: str
    competitors: list[str]
    target_score: dict[str, Any]
    competitor_scores: list[CompetitorScore]
    distribution: DistributionPosition
    gaps: list[CompetitiveGap]
    confidence_score: float
    fallback_used: bool = False
    fallback_explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize full brief output."""
        return {
            "target_company": self.target_company,
            "sector": self.sector,
            "generated_at": self.generated_at,
            "competitors": self.competitors,
            "target_score": self.target_score,
            "competitor_scores": [item.asdict() for item in self.competitor_scores],
            "distribution": self.distribution.asdict(),
            "gaps": [item.asdict() for item in self.gaps],
            "confidence_score": clamp_confidence(self.confidence_score),
            "fallback_used": bool(self.fallback_used),
            "fallback_explanation": self.fallback_explanation,
        }

