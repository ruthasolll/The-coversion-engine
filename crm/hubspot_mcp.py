from __future__ import annotations

import json
import os
import logging
import traceback
from datetime import datetime, timezone

from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput

from crm.mappers import build_enriched_contact_properties

logger = logging.getLogger(__name__)
ALLOWED_STATUSES = {"sent", "delivered", "bounced", "replied", "complained"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _debug_print_hubspot_called() -> None:
    try:
        print("🔥 HUBSPOT FUNCTION CALLED")

    except UnicodeEncodeError:
        print("HUBSPOT FUNCTION CALLED")


def _extract_hubspot_error(exc: Exception) -> tuple[str, int | None, str]:
    details = str(exc)
    status_code = getattr(exc, "status", None)
    body = str(getattr(exc, "body", "") or "")
    if body and body not in details:
        details = f"{details} | body={body}"
    return details, status_code, body


def _is_iso8601(value: str) -> bool:
    raw = (value or "").strip()
    if not raw:
        return False
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _validate_update_payload(email: str, properties: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if not email:
        issues.append("missing_email")
    if not isinstance(properties, dict) or not properties:
        issues.append("missing_properties")
        return False, issues

    for key, value in properties.items():
        if value is None:
            issues.append(f"{key}:none_value")
            continue
        if isinstance(value, str) and not value.strip():
            issues.append(f"{key}:empty_string")
            continue
        if key == "email_delivery_status":
            status = str(value).strip().lower()
            if status not in ALLOWED_STATUSES:
                issues.append(f"{key}:invalid_status:{status}")
        if key.endswith("_at") and isinstance(value, str):
            if not _is_iso8601(value):
                issues.append(f"{key}:invalid_iso8601")
    return len(issues) == 0, issues


class HubSpotMCP:
    def __init__(self) -> None:
        token = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
        self.client = HubSpot(access_token=token) if token else None

    def is_configured(self) -> bool:
        return self.client is not None

    def upsert_enriched_contact(
        self,
        lead: dict,
        icp_segment: str,
        enrichment: dict | None = None,
        enrichment_timestamp: str | None = None,
    ) -> dict:
        if not self.client:
            return {"ok": False, "error": "hubspot_not_configured"}

        email = str(lead.get("email", "")).strip()
        if not email:
            return {"ok": False, "error": "missing_email"}

        properties = build_enriched_contact_properties(
            lead=lead,
            icp_segment=icp_segment,
            enrichment=enrichment,
            enrichment_timestamp=enrichment_timestamp,
        )
        request = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email,
                        }
                    ]
                }
            ],
            "limit": 1,
            "properties": ["email"],
        }
        try:
            search_result = self.client.crm.contacts.search_api.do_search(public_object_search_request=request)
        except Exception as exc:
            logger.exception("hubspot_search_failed")
            return {"ok": False, "error": "hubspot_search_failed", "details": str(exc)}

        existing = getattr(search_result, "results", []) or []
        if existing:
            contact_id = existing[0].id
            try:
                self.client.crm.contacts.basic_api.update(
                    contact_id=contact_id,
                    simple_public_object_input=SimplePublicObjectInput(properties=properties),
                )
                return {"ok": True, "action": "updated", "contact_id": contact_id, "properties": properties, "status_code": 200}
            except Exception as e:
                logger.exception("hubspot_update_failed")
                details, status_code, body = _extract_hubspot_error(e)
                return {
                    "ok": False,
                    "error": "hubspot_update_failed",
                    "details": details,
                    "status_code": status_code,
                    "body": body,
                }

        try:
            created = self.client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=SimplePublicObjectInput(properties=properties)
            )
        except Exception as exc:
            logger.exception("hubspot_create_failed")
            return {"ok": False, "error": "hubspot_create_failed", "details": str(exc)}
        created_id = getattr(created, "id", "")
        return {"ok": True, "action": "created", "contact_id": created_id, "properties": properties}

    def update_contact_properties_by_email(self, email: str, properties: dict) -> dict:
        _debug_print_hubspot_called()
        logger.info("hubspot_update_triggered", extra={"email": email, "properties": properties})
        if not self.client:
            return {"ok": False, "error": "hubspot_not_configured"}
        if not email:
            return {"ok": False, "error": "missing_email"}
        if not properties:
            return {"ok": False, "error": "missing_properties"}

        validation_ok, validation_issues = _validate_update_payload(email=email, properties=properties)
        if not validation_ok:
            logger.warning(
                "hubspot_payload_invalid",
                extra={"email": email, "properties": properties, "validation_issues": validation_issues},
            )
            return {
                "ok": False,
                "error": "hubspot_payload_invalid",
                "details": "validation_failed",
                "validation": {"ok": False, "issues": validation_issues},
                "payload_sent": {"email": email, "properties": properties},
                "action": "skip_hubspot_call",
            }

        request = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email,
                        }
                    ]
                }
            ],
            "limit": 1,
            "properties": ["email"],
        }
        try:
            search_result = self.client.crm.contacts.search_api.do_search(public_object_search_request=request)
        except Exception as exc:
            logger.exception("hubspot_search_failed")
            return {"ok": False, "error": "hubspot_search_failed", "details": str(exc)}
        existing = getattr(search_result, "results", []) or []
        search_count = len(existing)
        logger.info(
            "hubspot_contact_search",
            extra={
                "email": email,
                "search_result_count": search_count,
                "matched_contact_ids": [getattr(item, "id", "") for item in existing[:5]],
            },
        )
        if not existing:
            create_properties = {"email": email, **properties}
            create_payload = SimplePublicObjectInput(properties=create_properties)
            logger.info(
                "hubspot_contact_not_found_creating",
                extra={"email": email, "properties": create_properties},
            )
            try:
                created = self.client.crm.contacts.basic_api.create(
                    simple_public_object_input_for_create=create_payload
                )
                created_id = getattr(created, "id", "")
                logger.info(
                    "hubspot_create_success",
                    extra={"email": email, "contact_id": created_id},
                )
                return {
                    "ok": True,
                    "contact_id": created_id,
                    "email": email,
                    "status_code": 201,
                    "action": "created",
                    "search_result_count": search_count,
                    "payload_sent": {"email": email, "properties": create_properties},
                    "validation": {"ok": True, "issues": []},
                }
            except Exception as e:
                logger.exception("hubspot_create_failed")
                details, status_code, body = _extract_hubspot_error(e)
                return {
                    "ok": False,
                    "error": "hubspot_create_failed",
                    "details": details,
                    "status_code": status_code,
                    "body": body,
                    "search_result_count": search_count,
                    "payload_sent": {"email": email, "properties": create_properties},
                    "validation": {"ok": True, "issues": []},
                    "trace": traceback.format_exc(),
                }

        contact_id = existing[0].id
        logger.info("IS HUBSPOT CALL ACTUALLY BEING EXECUTED?")
        logger.info("hubspot_update_call_entry", extra={"email": email, "contact_id": contact_id})
        logger.info("hubspot_payload", extra={"email": email, "properties": properties})
        try:
            update_response = self.client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input=SimplePublicObjectInput(properties=properties),
            )
            response_dict = update_response.to_dict() if hasattr(update_response, "to_dict") else {}
            logger.info(
                "hubspot_response",
                extra={"email": email, "status_code": 200, "response_text": str(response_dict)[:2000]},
            )
            logger.info(
                "hubspot_update_success",
                extra={"email": email, "properties": properties},
            )
            return {
                "ok": True,
                "contact_id": contact_id,
                "email": email,
                "status_code": 200,
                "action": "updated",
                "search_result_count": search_count,
                "payload_sent": {"email": email, "properties": properties},
                "response_body": response_dict,
                "validation": {"ok": True, "issues": []},
            }
        except Exception as e:
            logger.exception("hubspot_update_failed")
            details, status_code, body = _extract_hubspot_error(e)
            body_json: dict | None = None
            if body:
                try:
                    body_json = json.loads(body)
                except Exception:
                    body_json = None
            logger.error(
                "hubspot_response",
                extra={
                    "email": email,
                    "status_code": status_code,
                    "response_text": body,
                    "response_json": body_json,
                    "details": details,
                },
            )
            return {
                "ok": False,
                "error": "hubspot_update_failed",
                "details": details,
                "status_code": status_code,
                "body": body,
                "body_json": body_json,
                "search_result_count": search_count,
                "payload_sent": {"email": email, "properties": properties},
                "validation": {"ok": True, "issues": []},
                "trace": traceback.format_exc(),
            }

    def update_hubspot_contact(self, email: str, properties: dict) -> dict:
        """Compatibility wrapper for centralized HubSpot updates in channel handoff."""
        return self.update_contact_properties_by_email(email=email, properties=properties)

    def record_activity_by_email(self, email: str, activity_type: str, details: dict) -> dict:
        if not self.client:
            return {"ok": False, "error": "hubspot_not_configured"}
        if not email:
            return {"ok": False, "error": "missing_email"}

        properties = {
            "last_activity_type": activity_type,
            "last_activity_at": _utc_now(),
            "last_activity_details": str(details)[:1000],
        }
        update_result = self.update_contact_properties_by_email(email=email, properties=properties)
        if not update_result.get("ok"):
            return {
                "ok": False,
                "error": update_result.get("error", "activity_log_update_failed"),
                "details": update_result.get("details", ""),
                "email": email,
            }
        return {
            "ok": True,
            "action": "activity_logged",
            "activity_type": activity_type,
            "email": email,
            "properties": properties,
        }
