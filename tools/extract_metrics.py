#!/usr/bin/env python3
"""Extract stage-1 metrics from VASP outputs and write metrics.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from hydrogen_solubility.vasp_metrics import build_stage1_metrics_payload  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Parse VASP OUTCAR/OSZICAR for a run directory and write/update metrics.json."
        )
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Run directory (e.g., results/runs/20260302_Y_stage1_dft_001).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run id override (defaults to run directory name).",
    )
    parser.add_argument(
        "--outcar",
        default="raw/OUTCAR",
        help="OUTCAR path relative to run dir (default: raw/OUTCAR).",
    )
    parser.add_argument(
        "--oszicar",
        default="raw/OSZICAR",
        help="OSZICAR path relative to run dir (default: raw/OSZICAR).",
    )
    parser.add_argument(
        "--output",
        default="metrics.json",
        help="metrics output path relative to run dir (default: metrics.json).",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists():
        print(f"[FAIL] run directory not found: {run_dir}")
        return 1

    run_id = args.run_id or run_dir.name
    outcar = (run_dir / args.outcar).resolve()
    oszicar = (run_dir / args.oszicar).resolve()

    payload = build_stage1_metrics_payload(
        run_id=run_id,
        outcar_path=outcar,
        oszicar_path=oszicar,
    )

    # Keep artifact paths run-relative for stable provenance.
    payload["artifacts"]["outcar"] = args.outcar
    payload["artifacts"]["oszicar"] = args.oszicar

    output_path = (run_dir / args.output).resolve()
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"[OK] metrics written: {output_path}")
    print(f"  run_id: {run_id}")
    print(f"  status: {payload['status']}")
    print(f"  total_energy_eV: {payload['energetics']['total_energy_eV']}")
    print(f"  electronic_converged: {payload['checks']['electronic_converged']}")
    print(f"  ionic_converged: {payload['checks']['ionic_converged']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
