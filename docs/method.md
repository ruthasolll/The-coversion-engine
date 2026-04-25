# Act IV Mechanism Design Documentation

## 1. Purpose
This document specifies the **Act IV mechanism** used to prevent the target failure mode defined in [target_failure_mode.md](/Users/ruths/Desktop/TRP1/The-coversion-engine/evaluation/failure_taxonomy/target_failure_mode.md): **bench overcommitment** (over-promising talent readiness, fit, or timezone coverage).

The mechanism is designed so an engineer can re-implement it without reading code.

## 2. Root Failure and Design Rationale
### Root failure
Naive outbound systems infer demand from public signals and immediately claim delivery readiness. This fails when:
1. Hiring/AI signals are strong.
2. Real bench capability is weak or mismatched.
3. Outreach still promises immediate fit.

### Why naive systems fail
Naive flow:
1. Signal confidence high -> urgency high.
2. Urgency high -> assertive staffing promise.
3. No capability gate before message/send.

Result: high close-stage trust break and direct revenue loss.

### Act IV principle
**Never escalate claim strength above validated capability evidence.**  
Act IV binds outbound claims to explicit capability checks and a confidence-adjusted commitment policy.

## 3. Mechanism Scope
Act IV is applied after enrichment/scoring and before outbound commitment text is finalized.

Inputs:
1. Hiring Signal Brief (from hiring pipeline).
2. AI Maturity score result.
3. Bench capability snapshot.
4. Failure taxonomy risk priors.

Outputs:
1. Commitment tier (`conservative`, `qualified`, `confident`).
2. Allowed claims list.
3. Block/allow decision for outbound send.
4. Trace record for evaluation and ablations.

## 4. Input Schemas
### 4.1 HiringSignalBrief (required fields)
```json
{
  "company_name": "string",
  "generated_at": "ISO-8601",
  "signals": {
    "crunchbase": {"confidence": 0.0, "evidence": []},
    "jobs": {"confidence": 0.0, "job_titles": [], "job_count": 0, "job_velocity_60d": 0, "evidence": []},
    "layoffs": {"confidence": 0.0, "severity_score": 0.0, "evidence": []},
    "leadership": {"confidence": 0.0, "change_detected": false, "role_changed": null, "evidence": []}
  }
}
```

### 4.2 AIMaturityResult (required fields)
```json
{
  "score": 0,
  "confidence": 0.0,
  "justification": {"ai_hiring": "...", "ai_leadership": "..."},
  "evidence_summary": [],
  "timestamp": "ISO-8601"
}
```

### 4.3 BenchCapabilitySnapshot
```json
{
  "role_family": "ml_engineering|data_engineering|backend|fullstack|qa|devops",
  "ready_profiles_count": 0,
  "matching_domain_count": 0,
  "median_seniority_level": "junior|mid|senior|staff",
  "timezone_overlap_hours": 0,
  "last_validated_at": "ISO-8601"
}
```

### 4.4 FailureRiskPrior
```json
{
  "category": "bench_overcommitment",
  "aggregate_trigger_rate": 0.5433
}
```

## 5. Output Schema
```json
{
  "commitment_tier": "conservative|qualified|confident",
  "send_allowed": true,
  "claim_policy": {
    "allow_immediate_start_claim": false,
    "allow_exact_role_fit_claim": false,
    "allow_timezone_overlap_claim": true
  },
  "mitigation_reasons": ["..."],
  "mechanism_score": 0.0,
  "timestamp": "ISO-8601"
}
```

## 6. Act IV Processing Steps
1. **Normalize evidence quality**
   - `signal_strength = weighted_mean(hiring_signals.confidence, ai_maturity.confidence)`
2. **Compute capability score**
   - from `ready_profiles_count`, `matching_domain_count`, `median_seniority_level`, `timezone_overlap_hours`.
3. **Apply failure-risk penalty**
   - `risk_penalty = prior_bench_overcommitment_trigger_rate * trigger_decay_rate`.
4. **Compute commitment score**
   - `commitment_score = (w_signal * signal_strength) + (w_capability * capability_score) - risk_penalty`.
5. **Map score -> tier**
   - conservative/qualified/confident thresholds.
6. **Enforce claim policy**
   - strict claim gates by tier.
7. **Generate trace**
   - log all intermediate values for reproducibility.

## 7. Decision Logic
### 7.1 Capability score
```text
cap_ready = min(1.0, ready_profiles_count / max_ready_profiles)
cap_domain = min(1.0, matching_domain_count / max_domain_matches)
cap_timezone = min(1.0, timezone_overlap_hours / max_timezone_overlap)
cap_seniority = seniority_map[median_seniority_level]

capability_score =
  (weight_ready * cap_ready) +
  (weight_domain * cap_domain) +
  (weight_timezone * cap_timezone) +
  (weight_seniority * cap_seniority)
```

### 7.2 Signal strength
```text
signal_strength =
  (weight_jobs * jobs_confidence) +
  (weight_leadership * leadership_confidence) +
  (weight_crunchbase * crunchbase_confidence) +
  (weight_ai_maturity * ai_maturity_confidence)
```

### 7.3 Final mechanism score
```text
mechanism_score =
  (weight_signal_strength * signal_strength) +
  (weight_capability_strength * capability_score) -
  (bench_overcommitment_trigger_rate * trigger_decay_rate)
```

### 7.4 Tier mapping
```text
if mechanism_score < threshold_conservative:
    tier = "conservative"
elif mechanism_score < threshold_confident:
    tier = "qualified"
else:
    tier = "confident"
```

### 7.5 Claim gates
```text
conservative:
  immediate_start_claim = false
  exact_role_fit_claim = false
  timezone_overlap_claim = (cap_timezone >= threshold_timezone_min)

qualified:
  immediate_start_claim = (cap_ready >= threshold_ready_min)
  exact_role_fit_claim = (cap_domain >= threshold_domain_min)
  timezone_overlap_claim = true

confident:
  immediate_start_claim = true
  exact_role_fit_claim = true
  timezone_overlap_claim = true
```

## 8. Hyperparameters (Explicit)
```text
# signal aggregation
weight_jobs = 0.35
weight_leadership = 0.20
weight_crunchbase = 0.15
weight_ai_maturity = 0.30

# capability aggregation
weight_ready = 0.30
weight_domain = 0.35
weight_timezone = 0.15
weight_seniority = 0.20

# global combination
weight_signal_strength = 0.45
weight_capability_strength = 0.55

# risk control
trigger_decay_rate = 0.85
confidence_floor = 0.25

# normalization constants
max_ready_profiles = 8
max_domain_matches = 6
max_timezone_overlap = 6

# thresholds
threshold_conservative = 0.55
threshold_confident = 0.78
threshold_ready_min = 0.40
threshold_domain_min = 0.45
threshold_timezone_min = 0.30
```

## 9. Why This Fixes Root Cause
Bench overcommitment root cause is unchecked claim escalation. Act IV blocks this by:
1. making capability evidence mandatory in the score;
2. penalizing by known bench-overcommitment failure risk;
3. hard-gating high-risk claims by tier.

This addresses the cause (claim-capability mismatch), not only wording.

## 10. Test Protocol
### Unit tests
1. `mechanism_score` deterministic for fixed inputs.
2. tier boundary tests at exact thresholds.
3. claim-policy tests per tier.
4. penalty sensitivity test (`trigger_decay_rate` increase lowers confident rate).

### Integration tests
1. feed high signal + low capability -> must output `conservative`.
2. feed high signal + high capability -> may output `confident`.
3. ensure outbound payload never contains blocked claims.

### Invariants
1. `exact_role_fit_claim` cannot be true when `cap_domain < threshold_domain_min`.
2. `immediate_start_claim` cannot be true when `cap_ready < threshold_ready_min`.
3. `send_allowed=false` if all claim gates are false and confidence below floor.

## 11. Ablation Plan
### A0: Full Act IV (baseline)
Use full mechanism and track:
1. bench_overcommitment trigger rate
2. qualification-to-close conversion
3. trust-break incidents

### A1: Remove risk penalty
Set `trigger_decay_rate = 0` and compare deltas.

### A2: Remove capability branch
Set `weight_capability_strength = 0`, re-normalize signal weight to 1.0.

### A3: Remove claim gates
Keep score, disable policy gates.

Expected: A1-A3 each increase overcommitment incidents vs A0.

## 11.1 Statistical Significance Plan
Primary hypothesis:
- **H0**: Act IV does not reduce bench-overcommitment trigger rate versus baseline.
- **H1**: Act IV reduces bench-overcommitment trigger rate versus baseline.

Named test:
- **Two-proportion z-test** on failure rates (`failed_runs / total_runs`) comparing A0 vs each ablation (A1, A2, A3).

Significance threshold:
- `alpha = 0.05`
- Reject H0 if `p_value < 0.05`.

Interpretation rule:
1. If `p_value < 0.05` and A0 failure rate is lower, treat mitigation as statistically supported.
2. If `p_value >= 0.05`, treat difference as inconclusive and do not claim mitigation win.
3. Report both p-value and absolute effect size (`delta_failure_rate`) for each comparison.

Multiple comparisons handling:
- Since A0 is compared against 3 ablations, apply Bonferroni correction:
  - `alpha_corrected = 0.05 / 3 = 0.0167`
  - Final significance decision uses `p_value < 0.0167`.

Power/volume guideline:
- Minimum evaluation volume per arm: `n >= 200` qualified runs.
- If volume is below threshold, mark result as underpowered even if p-value is low.

## 12. Monitoring Outputs
Persist for every run:
1. input hashes (`hiring_signal_brief_id`, `bench_snapshot_id`)
2. all intermediate component scores
3. selected tier and blocked claims
4. final outbound decision

This enables replay, debugging, and postmortem root-cause verification.
