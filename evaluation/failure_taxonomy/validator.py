from __future__ import annotations

from evaluation.adversarial_probes.categories import CATEGORIES


def validate_taxonomy(probes: list[dict], taxonomy: dict) -> None:
    """Validate taxonomy completeness and one-to-one probe assignment."""
    categories = taxonomy.get("categories", {})
    assert set(categories.keys()) == set(CATEGORIES), "Taxonomy must include all 10 required categories."

    probe_ids_from_taxonomy: list[str] = []
    for category in CATEGORIES:
        entry = categories.get(category, {})
        probe_count = int(entry.get("probe_count", 0))
        probe_ids = list(entry.get("probe_ids", []))
        assert probe_count > 0, f"Category '{category}' must not be empty."
        assert len(probe_ids) == probe_count, f"Category '{category}' probe_count mismatch."
        assert "aggregate_trigger_rate" in entry, f"Category '{category}' missing aggregate_trigger_rate."
        assert "pattern_description" in entry and str(entry["pattern_description"]).strip(), (
            f"Category '{category}' missing pattern_description."
        )
        probe_ids_from_taxonomy.extend(probe_ids)

    assert len(probes) == len(probe_ids_from_taxonomy), "Total probe count must equal assigned probe count."
    assert len(set(probe_ids_from_taxonomy)) == len(probe_ids_from_taxonomy), "No probe can appear in multiple categories."

    source_probe_ids = {str(probe["probe_id"]) for probe in probes}
    taxonomy_probe_ids = set(probe_ids_from_taxonomy)
    assert source_probe_ids == taxonomy_probe_ids, "No orphan probes are allowed."

