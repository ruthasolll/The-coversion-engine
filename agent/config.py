from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent import load_yaml


@dataclass
class ConfigBundle:
    common: dict[str, Any]
    client: dict[str, Any]


def load_config(client: str) -> ConfigBundle:
    base = Path(__file__).resolve().parents[1]
    common = load_yaml(base / "config" / "common.yaml")
    client_cfg = load_yaml(base / "config" / "clients" / f"{client}.yaml")
    return ConfigBundle(common=common, client=client_cfg)
