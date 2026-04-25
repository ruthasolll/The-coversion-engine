from dotenv import load_dotenv
load_dotenv()

from integrations.sms_client import AfricasTalkingSMSClient

sms = AfricasTalkingSMSClient()

result = sms.send(
    phone="+251991148905",
    message="Test SMS from Conversion Engine"
)

print(
    {
        "ok": result.ok,
        "provider": result.provider,
        "status_code": result.status_code,
        "message": result.message,
        "dry_run": result.dry_run,
    }
)
