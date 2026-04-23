from __future__ import annotations

import json
from datetime import datetime, timezone

def lead_to_hubspot_contact(lead: dict) -> dict:
    return {
        "properties": {
            "email": lead.get("email", ""),
            "firstname": lead.get("first_name", ""),
            "lastname": lead.get("last_name", ""),
            "phone": lead.get("phone", ""),
        }
    }


def build_enriched_contact_properties(
    lead: dict,
    icp_segment: str,
    enrichment: dict | None = None,
    enrichment_timestamp: str | None = None,
) -> dict:
    enrichment = enrichment or {}
    timestamp = enrichment_timestamp or datetime.now(timezone.utc).isoformat()
    base = lead_to_hubspot_contact(lead)["properties"]
    base.update(
        {
            "icp_segment": icp_segment,
            "enrichment_timestamp": timestamp,
            "enrichment_payload_json": json.dumps(enrichment, sort_keys=True),
            "tenacious_status": "draft",
        }
    )
    return base
