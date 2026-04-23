from __future__ import annotations

import os

from hubspot import HubSpot


class HubSpotMCP:
    def __init__(self) -> None:
        token = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
        self.client = HubSpot(access_token=token) if token else None

    def is_configured(self) -> bool:
        return self.client is not None
