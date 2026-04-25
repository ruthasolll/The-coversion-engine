from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from agent.policies.compliance import passes_compliance
from agent.policies.confidence import passes_confidence
from agent.policies.stop_unsub import should_stop_or_unsubscribe
from enrichment.tenacious.ai_maturity import estimate_ai_maturity
from enrichment.tenacious.crunchbase import fetch_crunchbase
from enrichment.tenacious.jobs import fetch_job_signals
from enrichment.tenacious.layoffs import fetch_layoff_signals
from enrichment.tenacious.leadership import fetch_leadership

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jobs_url(company: str) -> str:
    cleaned = "".join(ch for ch in company.lower() if ch.isalnum())
    return f"https://{cleaned}.com/careers" if cleaned else "unknown"


@dataclass
class RunState:
    company: str
    timestamp: str = field(default_factory=_utc_now)
    signals_collected: list[dict] = field(default_factory=list)
    intermediate_confidence_updates: list[dict] = field(default_factory=list)
    belief_state: dict = field(default_factory=dict)
    run_trace: list[dict] = field(default_factory=list)
    plan: dict = field(default_factory=dict)


class Orchestrator:
    def __init__(self) -> None:
        self._step_fetchers: dict[str, Callable[[str], dict]] = {
            "fetch_crunchbase": fetch_crunchbase,
            "fetch_jobs": lambda company: fetch_job_signals(_jobs_url(company)),
            "fetch_layoffs": fetch_layoff_signals,
            "check_leadership": fetch_leadership,
            "compute_ai_maturity": estimate_ai_maturity,
        }
        self._fallback_sources: dict[str, str] = {
            "fetch_crunchbase": "https://www.crunchbase.com",
            "fetch_jobs": "unknown",
            "fetch_layoffs": "data/raw/layoffs.csv",
            "check_leadership": "https://duckduckgo.com",
            "compute_ai_maturity": "heuristic_public_signals",
        }

    def build_plan(self, company: str) -> dict:
        return {
            "company": company,
            "steps": [
                "fetch_crunchbase",
                "fetch_jobs",
                "fetch_layoffs",
                "check_leadership",
                "compute_ai_maturity",
            ],
        }

    def run(self, company: str) -> RunState:
        run_state = RunState(company=company.strip())
        run_state.plan = self.build_plan(run_state.company)
        for step in run_state.plan["steps"]:
            self._run_step(run_state, step)
        return run_state

    def _run_step(self, run_state: RunState, step: str) -> None:
        start = time.time()
        success = True
        error = ""

        try:
            fetcher = self._step_fetchers[step]
            raw_signal = fetcher(run_state.company)
            signal = self._normalize_signal(step=step, signal=raw_signal)
        except Exception as exc:  # pragma: no cover - defensive path
            success = False
            error = str(exc)
            logger.exception("enrichment_step_failed", extra={"company": run_state.company, "step": step})
            signal = self._fallback_signal(step=step, error=error)

        run_state.signals_collected.append(signal)
        run_state.belief_state[str(signal["signal"])] = {
            "value": signal["value"],
            "confidence": signal["confidence"],
            "source": signal["source"],
        }
        avg_confidence = round(
            sum(float(s.get("confidence", 0.0)) for s in run_state.signals_collected) / len(run_state.signals_collected),
            3,
        )
        run_state.intermediate_confidence_updates.append(
            {
                "step": step,
                "signal": signal["signal"],
                "confidence": signal["confidence"],
                "running_confidence": avg_confidence,
                "timestamp": _utc_now(),
            }
        )

        end = time.time()
        trace = {
            "step": step,
            "start_time": datetime.fromtimestamp(start, tz=timezone.utc).isoformat(),
            "end_time": datetime.fromtimestamp(end, tz=timezone.utc).isoformat(),
            "latency_ms": round((end - start) * 1000, 2),
            "success": success,
            "failure": None if success else error,
            "signal": signal["signal"],
            "confidence": signal["confidence"],
        }
        run_state.run_trace.append(trace)
        logger.info(
            "orchestrator_step_event",
            extra={
                "company": run_state.company,
                "step": step,
                "latency_ms": trace["latency_ms"],
                "success": success,
                "signal": signal["signal"],
                "confidence": signal["confidence"],
            },
        )

    def _normalize_signal(self, step: str, signal: dict) -> dict:
        if not isinstance(signal, dict):
            return self._fallback_signal(step=step, error="non_dict_signal")

        signal_name = str(signal.get("signal") or "unknown")
        value = str(signal.get("value")).strip() if signal.get("value") is not None else "unknown"
        source = str(signal.get("source")).strip() if signal.get("source") is not None else "unknown"
        timestamp = str(signal.get("timestamp")).strip() if signal.get("timestamp") is not None else _utc_now()
        if not value:
            value = "unknown"
        if not source:
            source = "unknown"
        if not timestamp:
            timestamp = _utc_now()
        try:
            confidence = float(signal.get("confidence", 0.1))
        except (TypeError, ValueError):
            confidence = 0.1
        return {
            "signal": signal_name,
            "value": value,
            "confidence": round(max(0.0, min(1.0, confidence)), 2),
            "source": source,
            "timestamp": timestamp,
        }

    def _fallback_signal(self, step: str, error: str) -> dict:
        return {
            "signal": "source_failure",
            "value": f"{step} failed: {error or 'unknown'}",
            "confidence": 0.1,
            "source": self._fallback_sources.get(step, "unknown"),
            "timestamp": _utc_now(),
        }


def evaluate_policies(payload: dict) -> tuple[bool, str]:
    if should_stop_or_unsubscribe(payload):
        return False, "stop_or_unsubscribe_detected"
    if not passes_compliance(payload):
        return False, "compliance_policy_block"
    if not passes_confidence(payload):
        return False, "confidence_threshold_not_met"
    return True, "ok"
