# t²-Bench Baseline (Interim)

We ran the official retail-domain baseline protocol (5 trials per task, 30 tasks; 150 simulations total) and recorded the benchmark output in `eval/score_log.json` and `eval/trace_log.jsonl`.

Observed aggregate result:
- pass@1: 0.7267
- 95% CI: [0.6504, 0.7917]
- p50 latency: 105.9521s
- p95 latency: 551.6491s
- average agent cost: $0.0199
- infra errors: 0

Method summary:
- Domain: retail baseline task pack
- Trials per task: 5
- Aggregation: pass@1 with bootstrap-style confidence interval from run outputs
- Provenance commit: `d11a97072c49d093f7b5a3e4fe9da95b490d43ba`

Interpretation:
- The baseline is serviceable but has wide uncertainty due to long-tail task variance.
- p95 latency indicates episodic stalls that should be prioritized before submission hardening.
- The trace file provides per-simulation outcomes and is linked to the same baseline run.

Caveat:
- This write-up is intentionally concise for interim submission and will be refreshed after the final task-specific run in this repo.
