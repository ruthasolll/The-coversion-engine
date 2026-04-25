from __future__ import annotations

from statistics import mean


def compute_average_trigger_rate(probes: list[dict]) -> float:
    """Compute average observed trigger rate for a category probe set."""
    if not probes:
        return 0.0
    values = [float(probe["observed_trigger_rate"]) for probe in probes]
    return round(mean(values), 4)

