#!/usr/bin/env python3
"""Generate a human-readable report.html for one run directory."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from hydrogen_solubility.reporting import write_run_report  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate report.html from manifest.json + metrics.json for a run directory."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Run directory (e.g., results/runs/20260302_Y_stage1_dft_001).",
    )
    parser.add_argument(
        "--output",
        default="report.html",
        help="Output HTML path relative to run dir (default: report.html).",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists():
        print(f"[FAIL] run directory not found: {run_dir}")
        return 1

    output_path = write_run_report(run_dir=run_dir, output_name=str(args.output))
    print(f"[OK] report written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
