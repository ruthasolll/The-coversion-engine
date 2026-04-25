# from enrichment.tenacious.crunchbase import fetch_crunchbase

# result = fetch_crunchbase("Stripe")
# print(result)

import json
from enrichment.tenacious.fusion_agent import run_fusion_enrichment

if __name__ == "__main__":
    company = "Stripe"

    result = run_fusion_enrichment(company)

    print("\n=== FUSION ENRICHMENT RESULT ===\n")
    print(json.dumps(result, indent=2))