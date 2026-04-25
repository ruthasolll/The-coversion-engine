from __future__ import annotations

import os
import logging
from datetime import datetime, timezone

from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput

from crm.mappers import build_enriched_contact_properties

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
                return {"ok": True, "action": "updated", "contact_id": contact_id, "properties": properties}
            except Exception as exc:
                logger.exception("hubspot_update_failed")
                return {"ok": False, "error": "hubspot_update_failed", "details": str(exc), "contact_id": contact_id}

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
        if not self.client:
            return {"ok": False, "error": "hubspot_not_configured"}
        if not email:
            return {"ok": False, "error": "missing_email"}
        if not properties:
            return {"ok": False, "error": "missing_properties"}

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
        if not existing:
            return {"ok": False, "error": "contact_not_found", "email": email}

        contact_id = existing[0].id
        try:
            self.client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input=SimplePublicObjectInput(properties=properties),
            )
            return {"ok": True, "contact_id": contact_id, "email": email}
        except Exception as exc:
            logger.exception("hubspot_update_failed")
            return {
                "ok": False,
                "error": "hubspot_update_failed",
                "details": str(exc),
                "contact_id": contact_id,
                "email": email,
            }

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

