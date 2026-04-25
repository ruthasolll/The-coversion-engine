from __future__ import annotations

import re

# Deterministic sector leader sets used when external APIs are unavailable.
# Selection criteria:
# 1) Similar industry keywords per sector.
# 2) Similar scale/funding profile by using established leaders with mature operations.
# 3) Known sector leaders likely representing top-quartile execution quality.
# 4) AI-forward companies are included where relevant to preserve competitive pressure.
_SECTOR_COMPETITORS: dict[str, list[str]] = {
    "fintech": [
        "Stripe",
        "Adyen",
        "Block",
        "PayPal",
        "Revolut",
        "Plaid",
        "Wise",
        "Checkout.com",
    ],
    "healthtech": [
        "Tempus",
        "Hims & Hers",
        "Teladoc",
        "Amwell",
        "OM1",
        "BenchSci",
        "K Health",
        "Ada Health",
    ],
    "saas": [
        "Atlassian",
        "HubSpot",
        "Salesforce",
        "ServiceNow",
        "Notion",
        "Datadog",
        "Asana",
        "Monday.com",
    ],
    "ecommerce": [
        "Shopify",
        "Amazon",
        "eBay",
        "Walmart",
        "Mercado Libre",
        "Etsy",
        "Wayfair",
        "Zalando",
    ],
    "cybersecurity": [
        "CrowdStrike",
        "Palo Alto Networks",
        "Zscaler",
        "Okta",
        "SentinelOne",
        "Cloudflare",
        "Fortinet",
        "Darktrace",
    ],
    "general": [
        "Microsoft",
        "Google",
        "Amazon",
        "Meta",
        "NVIDIA",
        "IBM",
        "Salesforce",
        "Oracle",
    ],
}

_SECTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fintech": ("fintech", "payments", "banking", "lending", "insurtech"),
    "healthtech": ("health", "med", "biotech", "care"),
    "saas": ("saas", "software", "b2b"),
    "ecommerce": ("commerce", "marketplace", "retail", "shopping"),
    "cybersecurity": ("security", "cyber", "identity", "threat"),
}


def infer_sector(company_name: str, sector: str | None = None, crunchbase_signal: dict | None = None) -> str:
    """Infer sector using explicit input first, then signal text, then fallback."""
    if sector and str(sector).strip():
        return str(sector).strip().lower()

    combined = company_name
    crunchbase_signal = crunchbase_signal or {}
    combined += " " + " ".join(str(item) for item in crunchbase_signal.get("evidence", []))
    combined += " " + str(crunchbase_signal.get("funding_stage", ""))
    lowered = combined.lower()

    for sector_name, keywords in _SECTOR_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return sector_name
    return "general"


def select_competitors(company_name: str, sector: str) -> tuple[list[str], bool, str]:
    """Return 5-10 deterministic top-quartile competitors for a sector."""
    normalized_sector = re.sub(r"[^a-z0-9]+", "", sector.strip().lower())
    matched_key = "general"
    for known in _SECTOR_COMPETITORS:
        if known == normalized_sector or known in normalized_sector or normalized_sector in known:
            matched_key = known
            break

    candidates = [name for name in _SECTOR_COMPETITORS.get(matched_key, _SECTOR_COMPETITORS["general"]) if name.lower() != company_name.strip().lower()]
    fallback_used = False
    fallback_explanation = ""

    if len(candidates) < 5:
        fallback_used = True
        fallback_explanation = (
            f"Sector '{sector}' had fewer than 5 deterministic leaders; "
            "used global AI-heavy leaders as fallback."
        )
        merged = candidates + [name for name in _SECTOR_COMPETITORS["general"] if name not in candidates and name.lower() != company_name.strip().lower()]
        candidates = merged

    return candidates[:10], fallback_used, fallback_explanation

