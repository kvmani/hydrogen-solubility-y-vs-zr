"""Canonical repository locations.

Every tool resolves paths through this module so that the layout described in
``docs/workflow.md`` is defined in exactly one place.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Repository root (``src/hydrogen_solubility/paths.py`` -> two levels up).
REPO_ROOT = Path(__file__).resolve().parents[2]

CONFIGS_DIR = REPO_ROOT / "configs"
GENERATED_CONFIGS_DIR = CONFIGS_DIR / "generated"
SITE_CONFIG_PATH = CONFIGS_DIR / "site.yaml"
SITE_EXAMPLE_PATH = CONFIGS_DIR / "site.example.yaml"


def results_dir() -> Path:
    """Project results workspace: index files, analysis and batch logs live here.

    Defaults to ``<repo>/results``; ``$HSOL_RESULTS_DIR`` overrides it (used by the
    test-suite). Run directories themselves go to ``site.paths.results_root``.
    """

    override = os.environ.get("HSOL_RESULTS_DIR")
    return Path(override).expanduser().resolve() if override else REPO_ROOT / "results"


def analysis_dir() -> Path:
    return results_dir() / "analysis"


def batch_log_dir() -> Path:
    return results_dir() / "batch_logs"


def site_config_path() -> Path:
    """Return the active site config path (``$HSOL_SITE`` overrides the default)."""

    override = os.environ.get("HSOL_SITE")
    return Path(override).expanduser().resolve() if override else SITE_CONFIG_PATH


def resolve_repo_path(raw: str | Path) -> Path:
    """Resolve a user path: absolute paths are kept, relative ones are repo-relative."""

    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def display_path(path: Path) -> str:
    """Render ``path`` relative to the repo root when possible (stable in provenance)."""

    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())
