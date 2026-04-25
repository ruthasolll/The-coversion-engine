from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def clamp_confidence(value: float) -> float:
    """Clamp a confidence score to the inclusive 0..1 range."""
    return max(0.0, min(1.0, round(float(value), 2)))


@dataclass
class BaseSignal:
    """Base shape used by every hiring-signal module."""

    timestamp: str
    source: str
    confidence: float
    evidence: list[str] = field(default_factory=list)

    def asdict(self) -> dict[str, Any]:
        """Serialize to a dictionary and normalize confidence."""
        payload = asdict(self)
        payload["confidence"] = clamp_confidence(self.confidence)
        return payload


@dataclass
class CrunchbaseSignal(BaseSignal):
    """Structured Crunchbase signal."""

    funding_stage: str | None = None
    last_funding_date: str | None = None
    investors: list[str] = field(default_factory=list)
    funding_filter_passed: bool = False


@dataclass
class JobsSignal(BaseSignal):
    """Structured jobs signal scraped from public pages."""

    job_count: int = 0
    job_titles: list[str] = field(default_factory=list)
    job_velocity_60d: int = 0
    baseline_job_count_60d: int = 0


@dataclass
class LayoffsSignal(BaseSignal):
    """Structured layoffs signal parsed from layoffs.fyi data."""

    last_layoff_date: str | None = None
    total_layoffs_12m: int = 0
    severity_score: float = 0.0


@dataclass
class LeadershipSignal(BaseSignal):
    """Structured leadership change signal."""

    change_detected: bool = False
    role_changed: str | None = None
    date: str | None = None


@dataclass
class HiringSignalBrief:
    """Top-level schema for pipeline output."""

    company_name: str
    generated_at: str
    crunchbase_signal: CrunchbaseSignal
    jobs_signal: JobsSignal
    layoffs_signal: LayoffsSignal
    leadership_signal: LeadershipSignal

    def to_output(self) -> dict[str, Any]:
        """Return rubric-aligned serialized output."""
        return {
            "company_name": self.company_name,
            "generated_at": self.generated_at,
            "signals": {
                "crunchbase": self.crunchbase_signal.asdict(),
                "jobs": self.jobs_signal.asdict(),
                "layoffs": self.layoffs_signal.asdict(),
                "leadership": self.leadership_signal.asdict(),
            },
        }

