# The Conversion Engine

The Conversion Engine is a pluggable outbound orchestration system supporting two editions:
- Tenacious (B2B AI-services sales motion)
- Acme (regulated/complaint-aware variant)

## Architecture

Core runtime layers:
- `agent/`: orchestration, routing, and policy enforcement.
- `channels/`: provider adapters for email (Resend/MailerSend), SMS (Africa's Talking), and voice.
- `enrichment/`: signal loaders and scoring helpers.
- `crm/` and `calendars/`: HubSpot and Cal.com integration points.
- `eval/`: tau-bench harness area plus score/trace artifacts.
- `evidence/` and `probes/`: claim graphing and targeted failure probes.

## Safety Kill Switch

Set `ALLOW_REAL_PROSPECT_CONTACT=false` in `.env` by default.

When `ALLOW_REAL_PROSPECT_CONTACT` is not explicitly `true`, provider send methods must run in dry-run mode and must not contact real prospects.

## Requirements

- Python 3.11+
- PowerShell (Windows scripts provided)
- Optional external accounts: Resend, MailerSend, Africa's Talking, HubSpot sandbox, Cal.com, Langfuse

## Setup

1. Run:
   `powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1`
2. Copy `.env.example` to `.env` and fill credentials.
3. Confirm safety default:
   `ALLOW_REAL_PROSPECT_CONTACT=false`
4. Run smoke checks:
   `powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1`
5. Start local API:
   `powershell -ExecutionPolicy Bypass -File scripts/run_local.ps1`

## Evaluation Artifacts

- Score log: `eval/score_log.json`
- Trace log: `eval/trace_log.jsonl`
- Baseline write-up: `deliverables/baseline.md`
- Signal enrichment rubric evidence: `deliverables/signal_enrichment_pipeline.md`

## Notes

- Current baseline files are carried from the official retail tau-bench baseline run metadata.
- For production integrations, complete provider webhook registration in `docs/day0_preflight.md`.
