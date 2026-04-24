from __future__ import annotations

from pathlib import Path

from enrichment.merge_pipeline import build_enrichment_artifact, save_enrichment_artifact


def build_signal_artifact(*, company: str, jobs_url: str) -> dict:
    artifact = build_enrichment_artifact(company=company, jobs_url=jobs_url)
    save_enrichment_artifact(artifact)
    return artifact


def save_signal_artifact(artifact: dict, output_path: Path | None = None) -> Path:
    return save_enrichment_artifact(artifact=artifact, output_path=output_path)
