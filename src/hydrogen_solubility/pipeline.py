"""Workflow placeholders for upcoming config-driven execution tasks."""

from __future__ import annotations


def load_config(path: str) -> dict:
    """Load and validate a run configuration (TODO)."""
    raise NotImplementedError("Config loading will be implemented in a future task.")


def write_manifest(run_dir: str, payload: dict) -> None:
    """Write manifest JSON according to docs/data_model.md (TODO)."""
    raise NotImplementedError("Manifest writing will be implemented in a future task.")


def write_metrics(run_dir: str, payload: dict) -> None:
    """Write metrics JSON according to docs/data_model.md (TODO)."""
    raise NotImplementedError("Metrics writing will be implemented in a future task.")
