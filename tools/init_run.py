#!/usr/bin/env python3
"""Initialize a standardized run directory from a validated config."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from hydrogen_solubility.run_bootstrap import RunInitializationError, init_run_from_config  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create results/runs/<run_id>/ layout from config and write starter "
            "manifest.json + metrics.json."
        )
    )
    parser.add_argument("config_path", help="Path to stage-1 config file.")
    parser.add_argument(
        "--results-root",
        default=None,
        help="Optional override for results root directory (default from config outputs.results_root).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting manifest/metrics and config snapshot if run directory already exists.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = init_run_from_config(
            config_path=args.config_path,
            results_root=args.results_root,
            force=args.force,
        )
    except (RunInitializationError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    print(f"[OK] run initialized: {result['run_id']}")
    print(f"  run_dir: {result['run_dir']}")
    print(f"  manifest: {result['manifest']}")
    print(f"  metrics: {result['metrics']}")
    print(f"  report: {result['report']}")
    print(f"  config_snapshot: {result['config_snapshot']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
