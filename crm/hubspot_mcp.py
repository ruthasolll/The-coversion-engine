from __future__ import annotations

import os

from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput

from crm.mappers import build_enriched_contact_properties


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
        search_result = self.client.crm.contacts.search_api.do_search(public_object_search_request=request)

        existing = getattr(search_result, "results", []) or []
        if existing:
            contact_id = existing[0].id
            self.client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input=SimplePublicObjectInput(properties=properties),
            )
            return {"ok": True, "action": "updated", "contact_id": contact_id, "properties": properties}

        created = self.client.crm.contacts.basic_api.create(
            simple_public_object_input_for_create=SimplePublicObjectInput(properties=properties)
        )
        created_id = getattr(created, "id", "")
        return {"ok": True, "action": "created", "contact_id": created_id, "properties": properties}
