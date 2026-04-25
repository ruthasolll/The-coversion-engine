from __future__ import annotations

from dataclasses import asdict, dataclass

from evaluation.adversarial_probes.categories import CATEGORIES


@dataclass(frozen=True)
class AdversarialProbe:
    """Structured adversarial probe definition."""

    probe_id: str
    category: str
    title: str
    setup: str
    expected_failure_signature: str
    observed_trigger_rate: float
    business_cost: str
    tenacious_specific: bool

    def to_dict(self) -> dict:
        """Serialize to a dictionary."""
        return asdict(self)


def validate_probe_dict(probe: dict) -> None:
    """Validate probe dictionary shape and value constraints."""
    required_fields = {
        "probe_id",
        "category",
        "title",
        "setup",
        "expected_failure_signature",
        "observed_trigger_rate",
        "business_cost",
        "tenacious_specific",
    }
    missing = required_fields.difference(probe.keys())
    if missing:
        raise ValueError(f"Probe missing fields: {sorted(missing)}")
    if probe["category"] not in CATEGORIES:
        raise ValueError(f"Invalid category: {probe['category']}")
    rate = float(probe["observed_trigger_rate"])
    if rate < 0.0 or rate > 1.0:
        raise ValueError(f"Invalid observed_trigger_rate for {probe['probe_id']}: {rate}")

