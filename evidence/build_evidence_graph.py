from __future__ import annotations

from pathlib import Path

import yaml


def build_graph(registry_path: Path) -> dict:
    with registry_path.open("r", encoding="utf-8") as handle:
        doc = yaml.safe_load(handle) or {}

    nodes = [{"id": c["id"], "owner": c["owner"]} for c in doc.get("claims", [])]
    edges = []
    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    graph = build_graph(base / "claim_registry.yaml")
    print(graph)
