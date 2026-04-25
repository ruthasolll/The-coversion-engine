# Setup and Bootstrapping

This guide is the operational bootstrap path for running The Conversion Engine locally and wiring external webhooks.

## 1) Prerequisites

- Python 3.11+
- Git
- PowerShell (Windows) or an equivalent shell
- Optional provider accounts: Resend, MailerSend, Africa's Talking, HubSpot, Cal.com, Langfuse

## 2) Install Dependencies

Option A (recommended in this repo):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
```

Option B (manual `pip` path):

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m playwright install chromium
```

## 3) Environment Variables

Copy the template first:

```powershell
Copy-Item .env.example .env
```

Variables currently used by code:

| Variable | Required | Used In | Purpose |
|---|---|---|---|
| `APP_ENV` | no | runtime convention | Environment label (`development`, `staging`, `prod`) |
| `CLIENT` | no | `agent/main.py` | Client config selector (`tenacious` default) |
| `LOG_LEVEL` | no | logging config convention | Logging verbosity |
| `ALLOW_REAL_PROSPECT_CONTACT` | yes | `integrations/sms_client.py` and safety policy | Kill switch; keep `false` unless explicitly approved |
| `RESEND_API_KEY` | for Resend sends | `channels/email/resend_adapter.py` | Resend API auth |
| `RESEND_FROM_EMAIL` | for Resend sends | `channels/email/resend_adapter.py` | Sender address |
| `RESEND_WEBHOOK_SECRET` | recommended | provider config | Secret for webhook validation (future enforcement) |
| `MAILERSEND_API_KEY` | for MailerSend sends | `channels/email/mailersend_adapter.py` | MailerSend API auth |
| `MAILERSEND_FROM_EMAIL` | for MailerSend sends | `channels/email/mailersend_adapter.py` | Sender address |
| `AFRICASTALKING_USERNAME` | for SMS sends | `channels/sms/africastalking_adapter.py` | Africa's Talking username (`sandbox` default) |
| `AFRICASTALKING_API_KEY` | for SMS sends | `channels/sms/africastalking_adapter.py` | Africa's Talking API auth |
| `AFRICASTALKING_WEBHOOK_SECRET` | recommended | `channels/sms/webhook.py`, `api/routes/sms_webhook.py` | Signature-presence gate for inbound SMS webhook |
| `LANGFUSE_PUBLIC_KEY` | optional | `channels/email/tracing.py` | Enables Langfuse tracing for email webhook pipeline |
| `LANGFUSE_SECRET_KEY` | optional | `channels/email/tracing.py` | Langfuse auth |
| `LANGFUSE_HOST` | optional | `channels/email/tracing.py` | Langfuse host (defaults to cloud) |
| `HUBSPOT_ACCESS_TOKEN` | for CRM writes | `crm/hubspot_mcp.py` | HubSpot API token |
| `HUBSPOT_PORTAL_ID` | optional | provider config/docs | HubSpot account metadata |
| `HUBSPOT_WEBHOOK_SECRET` | optional | provider config/docs | HubSpot webhook signature validation key (future enforcement) |
| `CALCOM_API_KEY` | for Cal.com calls | `calendars/calcom.py` | Cal.com API auth |
| `CALCOM_WEBHOOK_SECRET` | optional | provider config/docs | Cal.com webhook verification key (future enforcement) |
| `CALCOM_EVENT_TYPE_ID` | optional | runtime config | Default Cal.com event type |
| `WEBHOOK_BASE_URL` | recommended | deployment ops | Public base URL for webhook registration |
| `PLAYWRIGHT_BROWSERS_PATH` | optional | Playwright runtime | Browser binary location override |

## 4) Run Order (Local Startup)

1. Bootstrap dependencies.
2. Fill `.env` with provider keys and keep `ALLOW_REAL_PROSPECT_CONTACT=false` for safe testing.
3. Run smoke tests:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
   ```
4. Start API:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/run_local.ps1
   ```
5. Verify:
   - Health: `GET http://127.0.0.1:8000/health`
   - Enrichment run: `POST http://127.0.0.1:8000/enrichment/run`

## 5) Webhook Setup Instructions

Use your public tunnel/domain (for example from ngrok) and map provider webhooks to these endpoints.

### Email Webhooks

- Resend:
  - URL: `POST {WEBHOOK_BASE_URL}/webhooks/email/resend`
  - Events: sent, delivered, bounced, complained, replied
- MailerSend:
  - URL: `POST {WEBHOOK_BASE_URL}/webhooks/email/mailersend`
  - Events: sent, delivered, bounced, complained, reply/replied

### SMS Webhooks (Africa's Talking)

- Primary route:
  - URL: `POST {WEBHOOK_BASE_URL}/webhooks/sms/africastalking`
- Alternate route (legacy path still mounted):
  - URL: `POST {WEBHOOK_BASE_URL}/api/routes/sms_webhook/africastalking`
- If `AFRICASTALKING_WEBHOOK_SECRET` is set, requests without signature header are rejected.

### Calendar Webhooks (Cal.com)

- URL: `POST {WEBHOOK_BASE_URL}/webhooks/calendar/calcom`
- Booking events are normalized and can trigger HubSpot contact updates.

### CRM Webhooks (HubSpot)

- URL: `POST {WEBHOOK_BASE_URL}/webhooks/crm/hubspot`
- Current handler acknowledges events and returns count; enrich behavior as needed.

## 6) Safety and Production Guardrails

- Keep `ALLOW_REAL_PROSPECT_CONTACT=false` in local and CI test runs.
- Verify webhook payload validation in staging before enabling real provider traffic.
- Rotate provider API keys and webhook secrets regularly.

