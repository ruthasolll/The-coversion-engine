from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def clamp_confidence(value: float) -> float:
    """Clamp confidence to an inclusive 0..1 range."""
    return max(0.0, min(1.0, round(float(value), 2)))


@dataclass
class AIMaturityResult:
    """Structured AI maturity scoring result."""

    score: int
    confidence: float
    justification: dict[str, str] = field(default_factory=dict)
    evidence_summary: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to rubric-friendly dictionary output."""
        payload = asdict(self)
        payload["confidence"] = clamp_confidence(self.confidence)
        payload["score"] = int(max(0, min(3, int(self.score))))
        return payload

