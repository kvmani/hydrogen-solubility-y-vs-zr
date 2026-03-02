#!/usr/bin/env python3
"""Generate a Stage-1 host-validation convergence campaign from baseline configs."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from hydrogen_solubility.config_models import Stage1HostConfig, load_stage1_host_config  # noqa: E402


@dataclass(frozen=True)
class CampaignPoint:
    """One generated configuration point in the Stage-1 campaign."""

    sweep_type: str
    encut_eV: float
    kpoints_grid: tuple[int, int, int]
    source_run_id: str


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Stage-1 convergence configs (ENCUT/k-point sweeps) for Y/Zr host validation "
            "with deterministic run IDs and campaign plan metadata."
        )
    )
    parser.add_argument(
        "--base-config",
        dest="base_configs",
        action="append",
        required=True,
        help="Path to a baseline stage-1 config. Repeat for multiple systems.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory for generated configs and plan files. "
            "Default: configs/generated/stage1_campaign_<UTC timestamp>."
        ),
    )
    parser.add_argument(
        "--run-date",
        default=None,
        help="Run-id date token (YYYYMMDD). Default: current UTC date.",
    )
    parser.add_argument(
        "--start-seq",
        type=int,
        default=1,
        help="Starting sequence number per system (default: 1).",
    )
    parser.add_argument(
        "--sweeps",
        choices=("encut", "kpoints", "both"),
        default="both",
        help="Which sweep families to generate (default: both).",
    )
    parser.add_argument(
        "--include-reference",
        action="store_true",
        help="Also generate one reference config at baseline ENCUT+k-grid.",
    )
    parser.add_argument(
        "--set-results-root",
        default=None,
        help="Optional override for outputs.results_root in generated configs.",
    )
    parser.add_argument(
        "--write-json-plan",
        action="store_true",
        help="Also emit campaign plan JSON in addition to CSV.",
    )
    return parser


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _validate_run_date(token: str) -> str:
    if len(token) != 8 or not token.isdigit():
        raise ValueError("--run-date must match YYYYMMDD.")
    return token


def _run_id(*, run_date: str, system: str, seq: int) -> str:
    if seq < 1 or seq > 999:
        raise ValueError(f"seq out of supported range [1, 999]: {seq}")
    return f"{run_date}_{system}_stage1_dft_{seq:03d}"


def _kgrid_tag(grid: tuple[int, int, int]) -> str:
    return f"{grid[0]}x{grid[1]}x{grid[2]}"


def _encut_tag(encut: float) -> str:
    if float(encut).is_integer():
        return str(int(encut))
    return str(encut).replace(".", "p")


def _campaign_points(config: Stage1HostConfig, sweeps: str, include_reference: bool) -> list[CampaignPoint]:
    points: list[CampaignPoint] = []
    baseline = CampaignPoint(
        sweep_type="reference",
        encut_eV=config.vasp.encut_eV,
        kpoints_grid=config.vasp.kpoints_grid,
        source_run_id=config.run.run_id,
    )

    seen: set[tuple[str, float, tuple[int, int, int]]] = set()

    def add_point(point: CampaignPoint) -> None:
        key = (point.sweep_type, point.encut_eV, point.kpoints_grid)
        if key in seen:
            return
        seen.add(key)
        points.append(point)

    if include_reference:
        add_point(baseline)

    if sweeps in {"encut", "both"}:
        for encut in config.convergence_scan.encut_values_eV:
            add_point(
                CampaignPoint(
                    sweep_type="encut",
                    encut_eV=float(encut),
                    kpoints_grid=config.vasp.kpoints_grid,
                    source_run_id=config.run.run_id,
                )
            )

    if sweeps in {"kpoints", "both"}:
        for grid in config.convergence_scan.kpoint_grids:
            add_point(
                CampaignPoint(
                    sweep_type="kpoints",
                    encut_eV=config.vasp.encut_eV,
                    kpoints_grid=grid,
                    source_run_id=config.run.run_id,
                )
            )

    return points


def _objective(system: str, sweep_type: str, encut: float, kgrid: tuple[int, int, int]) -> str:
    if sweep_type == "encut":
        return (
            f"Stage-1 ENCUT sweep for alpha-{system} host: ENCUT={encut:.1f} eV at "
            f"fixed k-grid {_kgrid_tag(kgrid)}."
        )
    if sweep_type == "kpoints":
        return (
            f"Stage-1 k-point sweep for alpha-{system} host: k-grid {_kgrid_tag(kgrid)} at "
            f"fixed ENCUT={encut:.1f} eV."
        )
    return (
        f"Stage-1 reference host run for alpha-{system}: ENCUT={encut:.1f} eV, "
        f"k-grid {_kgrid_tag(kgrid)}."
    )


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _write_plan_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    fieldnames = [
        "run_id",
        "system",
        "sweep_type",
        "encut_eV",
        "kpoints_grid",
        "source_config",
        "config_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_generated_readme(path: Path, *, command: str, plan_csv: str) -> None:
    body = (
        "# Stage-1 Campaign Output\n\n"
        "Generated convergence campaign configs for Stage-1 host validation.\n\n"
        "## Generated With\n"
        f"`{command}`\n\n"
        "## Artifacts\n"
        f"- Plan CSV: `{plan_csv}`\n"
        "- Config files: one YAML per campaign point\n"
    )
    path.write_text(body, encoding="utf-8")


def main() -> int:
    args = _build_parser().parse_args()

    run_date = _validate_run_date(args.run_date) if args.run_date else _utc_date()
    if args.start_seq < 1 or args.start_seq > 999:
        raise ValueError("--start-seq must be in [1, 999].")

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else (REPO_ROOT / "configs" / "generated" / f"stage1_campaign_{_utc_timestamp()}").resolve()
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    seq_by_system: dict[str, int] = {}
    plan_rows: list[dict[str, str]] = []
    generated_count = 0

    for base in args.base_configs:
        base_path = Path(base).expanduser().resolve()
        config = load_stage1_host_config(base_path)

        system = config.run.system
        seq = seq_by_system.setdefault(system, args.start_seq)

        points = _campaign_points(config, sweeps=args.sweeps, include_reference=args.include_reference)

        for point in points:
            run_id = _run_id(run_date=run_date, system=system, seq=seq)
            seq += 1

            payload = config.model_dump(mode="json")
            payload["run"]["run_id"] = run_id
            payload["run"]["objective"] = _objective(
                system=system,
                sweep_type=point.sweep_type,
                encut=point.encut_eV,
                kgrid=point.kpoints_grid,
            )
            payload["vasp"]["encut_eV"] = point.encut_eV
            payload["vasp"]["kpoints_grid"] = list(point.kpoints_grid)

            if args.set_results_root:
                payload["outputs"]["results_root"] = args.set_results_root

            notes = list(payload.get("provenance", {}).get("notes", []))
            notes.extend(
                [
                    "Auto-generated by tools/plan_stage1_campaign.py.",
                    f"campaign_sweep={point.sweep_type}",
                    f"source_run_id={point.source_run_id}",
                ]
            )
            payload["provenance"]["notes"] = notes

            filename = (
                f"{run_id}__{point.sweep_type}__encut{_encut_tag(point.encut_eV)}"
                f"__k{_kgrid_tag(point.kpoints_grid)}.yaml"
            )
            config_out = output_dir / filename
            _write_yaml(config_out, payload)

            plan_rows.append(
                {
                    "run_id": run_id,
                    "system": system,
                    "sweep_type": point.sweep_type,
                    "encut_eV": str(point.encut_eV),
                    "kpoints_grid": _kgrid_tag(point.kpoints_grid),
                    "source_config": _relative(base_path),
                    "config_path": _relative(config_out),
                }
            )
            generated_count += 1

        seq_by_system[system] = seq

    plan_csv = output_dir / "stage1_campaign_plan.csv"
    _write_plan_csv(plan_csv, plan_rows)

    if args.write_json_plan:
        (output_dir / "stage1_campaign_plan.json").write_text(
            json.dumps(plan_rows, indent=2) + "\n", encoding="utf-8"
        )

    command_text = " ".join(sys.argv)
    _write_generated_readme(
        output_dir / "README.md",
        command=command_text,
        plan_csv=_relative(plan_csv),
    )

    print(f"[OK] generated configs: {generated_count}")
    print(f"[OK] output_dir: {_relative(output_dir)}")
    print(f"[OK] plan_csv: {_relative(plan_csv)}")
    if args.write_json_plan:
        print(f"[OK] plan_json: {_relative(output_dir / 'stage1_campaign_plan.json')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
