from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI

from agent.config import load_config
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
