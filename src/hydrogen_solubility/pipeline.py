"""Workflow placeholders for upcoming config-driven execution tasks."""

from __future__ import annotations

from pathlib import Path
import json

from .config_models import load_stage1_host_config
from .vasp_metrics import build_stage1_metrics_payload

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


def extract_and_write_metrics(
    run_dir: str,
    *,
    run_id: str | None = None,
    outcar_rel: str = "raw/OUTCAR",
    oszicar_rel: str = "raw/OSZICAR",
) -> dict:
    """Parse VASP outputs in a run directory and write `metrics.json`."""

    run_path = Path(run_dir).resolve()
    payload = build_stage1_metrics_payload(
        run_id=run_id or run_path.name,
        outcar_path=(run_path / outcar_rel).resolve(),
        oszicar_path=(run_path / oszicar_rel).resolve(),
    )
    payload["artifacts"]["outcar"] = outcar_rel
    payload["artifacts"]["oszicar"] = oszicar_rel
    write_metrics(str(run_path), payload)
    return payload
