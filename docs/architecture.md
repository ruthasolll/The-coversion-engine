# The Conversion Engine Architecture

This document is code-path aligned to the current repository state.

## System Diagram (Code-Mapped)

```mermaid
flowchart TD
    EXT[External Providers / Clients] --> MAIN[FastAPI App<br/>agent/main.py]

    MAIN --> EMAIL_WEBHOOK[Email Webhooks<br/>channels/email/webhook.py]
    MAIN --> SMS_WEBHOOK[SMS Webhooks<br/>channels/sms/webhook.py<br/>api/routes/sms_webhook.py]
    MAIN --> CAL_WEBHOOK[Calendar Webhook<br/>calendars/webhook.py]
    MAIN --> CRM_WEBHOOK[CRM Webhook<br/>crm/webhook.py]
    MAIN --> ROUTE_ENDPOINT[Routing Endpoint<br/>POST /route]
    MAIN --> ENRICH_ENDPOINT[Enrichment Endpoint<br/>POST /enrichment/run]

    ROUTE_ENDPOINT --> POLICY[Policy Evaluation<br/>agent/orchestrator.evaluate_policies<br/>agent/policies/*]
    POLICY --> CHANNEL_ROUTER[Channel Router<br/>agent/routing.py]
    CHANNEL_ROUTER --> EMAIL_ADAPTERS[Email Send Adapters<br/>channels/email/resend_adapter.py<br/>channels/email/mailersend_adapter.py]
    CHANNEL_ROUTER --> SMS_ADAPTER[SMS Adapter<br/>channels/sms/africastalking_adapter.py]
    CHANNEL_ROUTER --> VOICE_FALLBACK[Voice Fallback Adapter<br/>channels/voice/shared_rig_adapter.py]

    ENRICH_ENDPOINT --> EVIDENCE_PIPELINE[Signal Artifact Pipeline<br/>agent/evidence/pipeline.py]
    EVIDENCE_PIPELINE --> MERGE_PIPELINE[Merge Pipeline<br/>enrichment/merge_pipeline.py]
    MERGE_PIPELINE --> SRC_CB[Crunchbase<br/>enrichment/tenacious/crunchbase.py]
    MERGE_PIPELINE --> SRC_JOBS[Jobs (Playwright)<br/>enrichment/tenacious/jobs.py]
    MERGE_PIPELINE --> SRC_LAYOFFS[Layoffs<br/>enrichment/tenacious/layoffs.py]
    MERGE_PIPELINE --> SRC_LEADERSHIP[Leadership<br/>enrichment/tenacious/leadership.py]
    MERGE_PIPELINE --> SRC_AI[AI Maturity<br/>enrichment/tenacious/ai_maturity.py]

    EVIDENCE_PIPELINE --> FUSION[Fusion Agent<br/>enrichment/tenacious/fusion_agent.py]
    FUSION --> ORCH[Enrichment Orchestrator<br/>agent/orchestrator.Orchestrator]
    ORCH --> ORCH_SIGNALS[RunState.signals_collected]
    FUSION --> ARTIFACT[FusionArtifact<br/>signals + scores + run_trace]

    EMAIL_WEBHOOK --> EMAIL_HANDLER[Email Event Handler<br/>agent/handlers/email.py]
    EMAIL_HANDLER --> HUBSPOT[HubSpot MCP<br/>crm/hubspot_mcp.py]
    CAL_WEBHOOK --> HUBSPOT
    SMS_WEBHOOK --> SMS_HANDLER[SMS Handler<br/>agent/handlers/sms.py]

    EMAIL_WEBHOOK --> OBS[Observability<br/>Python logging + channels/email/tracing.py]
    SMS_WEBHOOK --> OBS
    ORCH --> OBS
    FUSION --> OBS
```

## Request Lifecycle

The system has multiple entry paths. The lifecycle below is the end-to-end agentic path aligned to actual modules:

1. Inbound request/webhook enters FastAPI (`agent/main.py`).
2. Request is normalized and validated at the boundary:
   - Email: `channels/email/webhook.py`
   - SMS: `channels/sms/webhook.py` or `api/routes/sms_webhook.py`
3. Orchestration/policy stage executes where applicable:
   - Route decisions: `evaluate_policies` in `agent/orchestrator.py` and `agent/routing.py`
   - Enrichment decisions: `Orchestrator.run` in `agent/orchestrator.py`
4. Enrichment collection runs by source module (Crunchbase/jobs/layoffs/leadership/AI maturity).
5. Fusion composes final intelligence in `enrichment/tenacious/fusion_agent.py`.
6. Downstream side effects occur by path:
   - Email events and calendar booking events can update HubSpot via `crm/hubspot_mcp.py`.
   - Channel route decisions target email/SMS/voice adapters.
7. Observability is emitted throughout:
   - Structured logs in handlers/webhooks/orchestrator/fusion.
   - Email webhook traces via `channels/email/tracing.py` when Langfuse env vars are configured.

## Failure Propagation Model

### Email Failure Path

- Location: `channels/email/webhook.py` -> `agent/handlers/email.py`.
- Behavior:
  - Malformed payload/event validation errors return HTTP `400` with structured error body.
  - Unexpected webhook exceptions return HTTP `500` with `internal_error`.
  - Downstream HubSpot failures are handled in `agent/handlers/email.py` with graceful degradation:
    - returns `ok=true` for known recoverable HubSpot issues (`hubspot_not_configured`, validation/property issues, contact not found, hubspot exception),
    - includes warning/action suffix `_degraded`,
    - logs exception and preserves webhook stability.

### Enrichment Failure Path

- Location: `agent/orchestrator.Orchestrator._run_step`.
- Behavior:
  - Any source exception is caught per step.
  - Fallback signal is emitted:
    - `signal: "source_failure"`
    - low confidence (`0.1`)
    - real source context (no fabricated source)
  - Step trace still records latency and failure details in `RunState.run_trace`.
  - Fusion continues with available signals; pipeline does not crash.

### CRM Failure Path

- Location: `crm/hubspot_mcp.py` callers in `agent/handlers/email.py` and `calendars/webhook.py`.
- Behavior:
  - Email path is fault-tolerant and degrades on HubSpot errors.
  - Calendar webhook returns result with `hubspot_update_failed` when update is unsuccessful.
  - Failures are surfaced in response payloads and logs; no silent failure path is intended.

## State Objects

### `EventState` (runtime event envelope; dict-based)

Used in webhook and handler flows (email/SMS). Representative fields:

- `event_type`
- `email` or `phone`
- `provider`
- `timestamp`
- `payload`

Primary producers/consumers:
- `channels/email/webhook.py` normalized event dict
- `agent/handlers/email.py` (`DownstreamEmailEvent`)
- `agent/handlers/sms.py` (`DownstreamSMSEvent`)

### `EnrichmentState` (`RunState` in code)

Concrete object: `agent/orchestrator.py:RunState`.

Fields:
- `company`
- `timestamp`
- `signals_collected`
- `intermediate_confidence_updates`
- `belief_state`
- `run_trace`
- `plan`

### `FusionArtifact` (dict returned by fusion)

Concrete producer: `enrichment/tenacious/fusion_agent.py:run_fusion_enrichment`.

Fields:
- `company`
- `signals`
- `fusion_summary`
- `overall_confidence`
- `risk_score`
- `opportunity_score`
- `risk_reasoning`
- `opportunity_reasoning`
- `plan`
- `belief_state`
- `intermediate_confidence_updates`
- `run_trace`
- `timestamp`

## System Invariants

1. Grounded honesty enforcement:
   - Missing values are normalized to `"unknown"` instead of fabricated content (`agent/orchestrator.py`).
   - Source failures become explicit `source_failure` signals with reduced confidence.
2. Confidence thresholds and bounds:
   - Policy gate: `passes_confidence` requires score `>= 0.7` (`agent/policies/confidence.py`).
   - Enrichment/fusion confidence values are clamped to `[0.0, 1.0]`.
3. Idempotency expectations:
   - Webhook handlers are expected to be safe on repeated events and return structured outcomes.
   - Explicit deduplication keys/replay protection are not yet fully implemented across all providers; repeated provider delivery may reprocess the same event.

## Diagram-to-Code Mapping Checklist

- FastAPI app and route registration: `agent/main.py`
- Policy engine: `agent/orchestrator.py`, `agent/policies/*`
- Channel routing: `agent/routing.py`
- Email webhook + tracing + handling: `channels/email/webhook.py`, `channels/email/tracing.py`, `agent/handlers/email.py`
- SMS webhook + handling: `channels/sms/webhook.py`, `api/routes/sms_webhook.py`, `agent/handlers/sms.py`
- Enrichment orchestration: `agent/orchestrator.Orchestrator`
- Source modules: `enrichment/tenacious/*.py`
- Fusion engine: `enrichment/tenacious/fusion_agent.py`
- CRM/calendar integration: `crm/hubspot_mcp.py`, `calendars/webhook.py`, `calendars/calcom.py`
- Observability: logging across above modules plus Langfuse integration in `channels/email/tracing.py`
