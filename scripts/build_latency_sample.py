from __future__ import annotations

import json
from pathlib import Path
from statistics import median


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    rank = (len(values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(values) - 1)
    frac = rank - low
    return values[low] + (values[high] - values[low]) * frac


def main() -> None:
    trace_path = Path("eval/trace_log.jsonl")
    out_path = Path("deliverables/latency_sample.json")

    rows = []
    with trace_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))

    sample = rows[:20]
    latencies = [float(r.get("duration", 0.0)) for r in sample]

    report = {
        "sample_size": len(sample),
        "source": "tau2 trace sample (not live provider traffic)",
        "p50_seconds": round(median(latencies), 4) if latencies else 0.0,
        "p95_seconds": round(percentile(latencies, 0.95), 4) if latencies else 0.0,
        "records": sample,
    }

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
