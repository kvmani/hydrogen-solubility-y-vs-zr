#!/usr/bin/env python3
"""Validate stage-1 YAML/JSON config files against project schema."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from hydrogen_solubility import ConfigValidationError, load_stage1_host_config  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate stage-1 host config files for Y/Zr baseline runs."
    )
    parser.add_argument(
        "config_paths",
        nargs="+",
        help="One or more config files (.yaml/.yml/.json).",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    has_error = False
    for raw_path in args.config_paths:
        path = Path(raw_path)
        try:
            cfg = load_stage1_host_config(path)
        except ConfigValidationError as exc:
            has_error = True
            print(f"[FAIL] {path}\n{exc}\n")
            continue

        print(
            "[OK] "
            f"{path} | run_id={cfg.run.run_id} | system={cfg.run.system} | "
            f"encut={cfg.vasp.encut_eV} eV | kmesh={cfg.vasp.kpoints_grid}"
        )

    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
