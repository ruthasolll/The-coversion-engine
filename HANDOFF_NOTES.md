# Handoff Notes

This file is for new engineers taking ownership of The Conversion Engine.

## Current Strengths

- End-to-end FastAPI ingress with mounted routes for email, SMS, calendar, and CRM hooks.
- Multi-source enrichment supports Crunchbase, jobs (Playwright), layoffs, leadership, and AI maturity.
- Agentic enrichment orchestration now includes plan, belief state, confidence updates, and per-step run trace.
- Fusion artifact includes confidence, risk/opportunity scores, and reasoning text.
- Email and SMS paths include normalization and downstream handler entrypoints.

## Known Limitations

- Voice channel is currently a placeholder adapter (`shared_rig_adapter`) and not full telephony.
- Webhook signature checks are partial in some paths (for example SMS checks signature presence, not full cryptographic verification).
- Some HubSpot property writes may require matching custom properties to exist in the target portal.
- Enrichment sources depend on public pages and may degrade under anti-bot restrictions or source HTML changes.
- There are overlapping SMS webhook paths (`/webhooks/sms/africastalking` and `/api/routes/sms_webhook/africastalking`) that should be consolidated when safe.
- Observability is mixed between standard logging and Langfuse email tracing; non-email traces are currently log-first.

## Missing Features (for Full Production Hardening)

- Unified secret verification middleware for all webhook providers.
- Idempotency keys and replay protection for inbound webhooks.
- Background task queue for long-running enrichment and retry policies.
- Strong schema contracts for every outbound/inbound event (pydantic models with versioning).
- Centralized mechanism-design docs for probes, failure taxonomy, and scoring governance in one canonical spec.
- CI workflow that runs lint + tests + smoke checks on every PR.

## Suggested Next Steps (First Week)

1. Consolidate webhook validation and add deterministic signature verification for Resend, MailerSend, Cal.com, and HubSpot.
2. Add contract tests for all webhook payload variants (good, malformed, missing fields, bounced/complained cases).
3. Add queue-backed enrichment execution with timeout/retry and explicit dead-letter behavior.
4. Define and document a versioned artifact schema for fusion outputs and run traces.
5. Replace or extend voice fallback adapter with a production provider integration.
6. Unify docs and report outputs so architecture, setup, and rubric evidence stay synchronized.

## Operational Tips

- Keep `ALLOW_REAL_PROSPECT_CONTACT=false` for local and CI by default.
- Use a staging HubSpot portal with all expected custom properties before enabling webhook-driven writes.
- Validate Playwright browser availability after environment setup (`scripts/smoke_test.ps1`).
- For debugging webhook failures, start from `channels/email/webhook.py` and `channels/sms/webhook.py` logs, then follow downstream handlers.

