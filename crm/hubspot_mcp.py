from __future__ import annotations

import os

from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput


class HubSpotMCP:
    def __init__(self) -> None:
        token = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
        self.client = HubSpot(access_token=token) if token else None

    def is_configured(self) -> bool:
        return self.client is not None

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
        search_result = self.client.crm.contacts.search_api.do_search(public_object_search_request=request)
        existing = getattr(search_result, "results", []) or []
        if not existing:
            return {"ok": False, "error": "contact_not_found", "email": email}

        contact_id = existing[0].id
        self.client.crm.contacts.basic_api.update(
            contact_id=contact_id,
            simple_public_object_input=SimplePublicObjectInput(properties=properties),
        )
        return {"ok": True, "contact_id": contact_id, "email": email}
