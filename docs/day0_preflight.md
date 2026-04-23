# Day 0 Preflight

## 1) Create a public webhook base URL (Render recommended)
1. Create a new Render Web Service from this repo.
2. Build command: `pip install -r requirements.txt`.
3. Start command: `python -m uvicorn agent.main:app --host 0.0.0.0 --port $PORT`.
4. After deploy, copy your service URL, for example: `https://conversion-engine.onrender.com`.
5. Put this in `.env` as `WEBHOOK_BASE_URL`.

## 2) Register webhook endpoints
- Resend inbound/replies: `${WEBHOOK_BASE_URL}/webhooks/email/resend`
- MailerSend events: `${WEBHOOK_BASE_URL}/webhooks/email/mailersend`
- Africa's Talking callbacks: `${WEBHOOK_BASE_URL}/webhooks/sms/africastalking`
- Cal.com bookings/events: `${WEBHOOK_BASE_URL}/webhooks/calendar/calcom`
- HubSpot webhooks: `${WEBHOOK_BASE_URL}/webhooks/crm/hubspot`

## 3) Credentials checklist for `.env`
- `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_WEBHOOK_SECRET`
- `MAILERSEND_API_KEY`, `MAILERSEND_FROM_EMAIL`
- `AFRICASTALKING_USERNAME`, `AFRICASTALKING_API_KEY`, `AFRICASTALKING_WEBHOOK_SECRET`
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
- `HUBSPOT_ACCESS_TOKEN`, `HUBSPOT_PORTAL_ID`, `HUBSPOT_WEBHOOK_SECRET`
- `CALCOM_API_KEY`, `CALCOM_WEBHOOK_SECRET`, `CALCOM_EVENT_TYPE_ID`

## 4) Local setup
- Run `scripts/bootstrap.ps1`
- Fill `.env`
- Run `scripts/smoke_test.ps1`
- Start app with `scripts/run_local.ps1`
