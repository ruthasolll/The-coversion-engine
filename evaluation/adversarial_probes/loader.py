from __future__ import annotations

import json
from pathlib import Path

from evaluation.adversarial_probes.schema import validate_probe_dict


def load_probes() -> list[dict]:
    """Load probes from sample_probes.json and validate structure."""
    path = Path(__file__).resolve().parent / "sample_probes.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("sample_probes.json must contain a JSON array.")
    for probe in data:
        if not isinstance(probe, dict):
            raise ValueError("Each probe must be a JSON object.")
        validate_probe_dict(probe)
    return data

