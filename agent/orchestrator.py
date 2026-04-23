from __future__ import annotations

from agent.policies.confidence import passes_confidence
from agent.policies.compliance import passes_compliance
from agent.policies.stop_unsub import should_stop_or_unsubscribe


def evaluate_policies(payload: dict) -> tuple[bool, str]:
    if should_stop_or_unsubscribe(payload):
        return False, "stop_or_unsubscribe_detected"
    if not passes_compliance(payload):
        return False, "compliance_policy_block"
    if not passes_confidence(payload):
        return False, "confidence_threshold_not_met"
    return True, "ok"
