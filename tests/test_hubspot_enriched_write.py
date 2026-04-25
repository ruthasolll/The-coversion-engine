from __future__ import annotations

import unittest
from types import SimpleNamespace

from crm.hubspot_mcp import HubSpotMCP


class FakeSearchAPI:
    def __init__(self, existing_id: str | None) -> None:
        self.existing_id = existing_id
        self.last_request = None

    def do_search(self, public_object_search_request: dict) -> SimpleNamespace:
        self.last_request = public_object_search_request
        if self.existing_id:
            return SimpleNamespace(results=[SimpleNamespace(id=self.existing_id)])
        return SimpleNamespace(results=[])


class FakeBasicAPI:
    def __init__(self) -> None:
        self.created = None
        self.updated = None

    def create(self, simple_public_object_input_for_create):
        self.created = simple_public_object_input_for_create
        return SimpleNamespace(id="new-contact-123")

    def update(self, contact_id: str, simple_public_object_input):
        self.updated = {"contact_id": contact_id, "payload": simple_public_object_input}
        return SimpleNamespace(id=contact_id)


class FakeContacts:
    def __init__(self, existing_id: str | None) -> None:
        self.search_api = FakeSearchAPI(existing_id=existing_id)
        self.basic_api = FakeBasicAPI()


class FakeCRM:
    def __init__(self, existing_id: str | None) -> None:
        self.contacts = FakeContacts(existing_id=existing_id)


class FakeHubSpotClient:
    def __init__(self, existing_id: str | None) -> None:
        self.crm = FakeCRM(existing_id=existing_id)


class HubSpotEnrichedWriteTests(unittest.TestCase):
    def test_upsert_creates_with_required_enrichment_fields(self) -> None:
        mcp = HubSpotMCP()
        mcp.client = FakeHubSpotClient(existing_id=None)
        result = mcp.upsert_enriched_contact(
            lead={"email": "lead@example.org", "first_name": "Amina", "last_name": "Njoroge"},
            icp_segment="mid_market_fintech",
            enrichment={"jobs_signal": "hiring"},
            enrichment_timestamp="2026-04-23T09:00:00+03:00",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "created")
        self.assertEqual(result["properties"]["icp_segment"], "mid_market_fintech")
        self.assertEqual(result["properties"]["enrichment_timestamp"], "2026-04-23T09:00:00+03:00")
        self.assertIn("jobs_signal", result["properties"]["enrichment_payload_json"])
        self.assertEqual(result["properties"]["tenacious_status"], "draft")

    def test_upsert_updates_existing_contact(self) -> None:
        mcp = HubSpotMCP()
        mcp.client = FakeHubSpotClient(existing_id="contact-42")
        result = mcp.upsert_enriched_contact(
            lead={"email": "lead@example.org"},
            icp_segment="enterprise_fintech",
            enrichment={"layoffs_signal": "none"},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "updated")
        self.assertEqual(result["contact_id"], "contact-42")

    def test_upsert_requires_email(self) -> None:
        mcp = HubSpotMCP()
        mcp.client = FakeHubSpotClient(existing_id=None)
        result = mcp.upsert_enriched_contact(
            lead={},
            icp_segment="enterprise_fintech",
            enrichment={},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "missing_email")

    def test_update_contact_properties_validation_failure_skips_hubspot_call(self) -> None:
        mcp = HubSpotMCP()
        fake_client = FakeHubSpotClient(existing_id="contact-42")
        mcp.client = fake_client
        result = mcp.update_contact_properties_by_email(
            email="lead@example.org",
            properties={
                "email_delivery_status": "invalid-status",
                "last_email_bounced_at": "not-an-iso-time",
            },
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "hubspot_payload_invalid")
        self.assertEqual(result["action"], "skip_hubspot_call")
        self.assertIsNone(fake_client.crm.contacts.basic_api.updated)

    def test_update_contact_properties_creates_when_contact_missing(self) -> None:
        mcp = HubSpotMCP()
        fake_client = FakeHubSpotClient(existing_id=None)
        mcp.client = fake_client
        result = mcp.update_contact_properties_by_email(
            email="newlead@example.org",
            properties={"email_delivery_status": "delivered", "last_email_provider": "resend"},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "created")
        self.assertEqual(result["status_code"], 201)
        self.assertEqual(result["search_result_count"], 0)
        self.assertIsNotNone(fake_client.crm.contacts.basic_api.created)


if __name__ == "__main__":
    unittest.main()
