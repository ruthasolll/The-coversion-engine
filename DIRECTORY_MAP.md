# Directory Map

Top-level structure for The Conversion Engine.

- `agent/`: Core runtime logic (routing, policies, handlers, orchestration, config loading).
- `api/`: API route modules that are mounted into the FastAPI app.
- `calendars/`: Cal.com client and webhook processing.
- `channels/`: Channel adapters and webhook handlers for email, SMS, and voice fallback.
- `config/`: YAML configuration bundles (`common` + client-specific configs).
- `crm/`: HubSpot MCP client logic and CRM webhook endpoint.
- `data/`: Local raw datasets used by enrichment loaders (for example layoffs fixtures).
- `deliverables/`: Submission artifacts and rubric documentation outputs.
- `docs/`: Human documentation (architecture, preflight, reports).
- `enrichment/`: Signal-fetch modules, fusion logic, merge utilities, confidence/scoring helpers.
- `eval/`: Tau benchmark harness artifacts and evaluation logs.
- `evidence/`: Evidence and claim-layer assets used by outbound reasoning workflows.
- `integrations/`: Integration wrappers and client-facing integration helpers.
- `knowledge_base/`: Static reference knowledge used by prompts/reasoning workflows.
- `langfuse/`: Langfuse-related helpers, experiments, or assets.
- `probes/`: Probe specifications and failure taxonomy testing assets.
- `scripts/`: Bootstrap, smoke-test, and local run scripts.
- `tests/`: Unit tests and integration tests for handlers, routing, enrichment, and sync logic.
- `.env.example`: Environment variable template for local setup.
- `README.md`: Project overview and high-level setup entrypoint.
- `SETUP.md`: Detailed bootstrapping and webhook wiring guide.
- `HANDOFF_NOTES.md`: Transfer notes for incoming engineers.

Machine-local or generated directories:

- `.venv/`: Local virtual environment; not part of app logic.
- `.codex/`: Local tooling runtime metadata.

