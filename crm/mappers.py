from __future__ import annotations


def lead_to_hubspot_contact(lead: dict) -> dict:
    return {
        "properties": {
            "email": lead.get("email", ""),
            "firstname": lead.get("first_name", ""),
            "lastname": lead.get("last_name", ""),
            "phone": lead.get("phone", ""),
        }
    }
