from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI

from agent.channel_handoff import ChannelHandoffManager
from api.routes.sms_webhook import router as sms_webhook_v2_router
from agent.config import load_config
from agent.evidence.pipeline import build_signal_artifact
from agent.orchestrator import evaluate_policies
from agent.routing import select_channel
from calendars.webhook import router as calendar_webhook_router
from channels.email.webhook import router as email_webhook_router
from channels.sms.webhook import router as sms_webhook_router
from crm.webhook import router as crm_webhook_router


load_dotenv()
app = FastAPI(title="Conversion Engine")
app.include_router(email_webhook_router)
app.include_router(sms_webhook_router)
app.include_router(sms_webhook_v2_router)
app.include_router(calendar_webhook_router)
app.include_router(crm_webhook_router)


@app.get("/health")
def health() -> dict:
    client = os.getenv("CLIENT", "tenacious")
    cfg = load_config(client)
    return {
        "status": "ok",
        "client": cfg.client.get("client", client),
        "signals": cfg.client.get("signals", []),
    }


@app.post("/route")
def route(payload: dict) -> dict:
    passed, reason = evaluate_policies(payload)
    if not passed:
        return {"status": "blocked", "reason": reason}
    channel, routing_reason = select_channel(payload)
    return {
        "status": "accepted",
        "channel": channel,
        "reason": routing_reason,
    }


@app.post("/enrichment/run")
def run_enrichment(payload: dict) -> dict:
    company = str(payload.get("company", "")).strip()
    jobs_url = str(payload.get("jobs_url", "https://example.com")).strip()
    email = str(payload.get("email", "")).strip().lower()
    if not company:
        return {"ok": False, "error": "missing_company"}
    artifact = build_signal_artifact(company=company, jobs_url=jobs_url)
    crm_result = {"ok": False, "action": "skipped_missing_email"}
    if email:
        crm_result = ChannelHandoffManager().process_enrichment_to_crm(email=email, artifact=artifact)
    return {"ok": True, "artifact": artifact, "crm_sync": crm_result}

