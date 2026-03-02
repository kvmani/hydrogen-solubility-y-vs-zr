"""Workflow placeholders for upcoming config-driven execution tasks."""

from __future__ import annotations

from pathlib import Path
import json

from .config_models import load_stage1_host_config

def load_config(path: str) -> dict:
    """Load and validate a stage-1 host config from YAML/JSON."""

    model = load_stage1_host_config(path)
    return model.model_dump(mode="json")


def write_manifest(run_dir: str, payload: dict) -> None:
    """Write manifest JSON according to docs/data_model.md."""

    output_path = Path(run_dir) / "manifest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_metrics(run_dir: str, payload: dict) -> None:
    """Write metrics JSON according to docs/data_model.md."""

    output_path = Path(run_dir) / "metrics.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
