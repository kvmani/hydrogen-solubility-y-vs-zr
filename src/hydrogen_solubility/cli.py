"""``hsol`` - the single command-line entry point of the project.

Typical sequence for one stage (details: docs/workflow.md)::

    hsol doctor                                   # check the environment once
    hsol plan    configs/campaigns/<stage>.yaml   # campaign -> run configs
    hsol prepare configs/generated/<stage>        # run dirs + INCAR/KPOINTS/POSCAR/POTCAR
    hsol run --mode dryrun configs/generated/<stage>
    hsol run --mode smoke  configs/generated/<stage>
    hsol run --mode submit configs/generated/<stage>
    hsol status                                   # progress board (+ results/INDEX.md)
    hsol collect                                  # parse finished runs
    hsol analyze convergence | solubility

Every command accepts files or directories of run configs where configs are needed,
continues past individual failures, prints a summary and exits non-zero if
anything failed.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from . import __version__
from .config_models import ConfigValidationError, SiteConfig, collect_config_paths, load_run_config, load_site_config
from .paths import SITE_EXAMPLE_PATH, batch_log_dir, display_path, resolve_repo_path, site_config_path
from .provenance import utc_stamp


def _ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def _site() -> SiteConfig:
    return load_site_config()


def _configs(paths: Sequence[str]) -> List[Path]:
    return collect_config_paths(list(paths))


def _summary(total: int, failed: int, what: str) -> int:
    print(f"\n{what}: {total - failed}/{total} succeeded" + (f", {failed} failed" if failed else ""))
    return 1 if failed else 0


# ----------------------------------------------------------------------------- commands


def cmd_validate(args: argparse.Namespace) -> int:
    failed = 0
    paths = _configs(args.configs)
    for path in paths:
        try:
            cfg = load_run_config(path)
        except ConfigValidationError as exc:
            failed += 1
            _fail(str(exc))
            continue
        deps = f" | needs {', '.join(cfg.dependencies())}" if cfg.dependencies() else ""
        _ok(f"{cfg.run_id} ({cfg.run.calc_type}){deps}")
    return _summary(len(paths), failed, "validate")


def cmd_plan(args: argparse.Namespace) -> int:
    from .planner import PlanError, write_plan

    try:
        out, planned, removed = write_plan(
            resolve_repo_path(args.campaign), resolve_repo_path(args.output_dir) if args.output_dir else None
        )
    except (PlanError, ConfigValidationError) as exc:
        _fail(str(exc))
        return 1
    for item in planned:
        deps = item.config.dependencies()
        _ok(f"{item.config.run_id:<34} {item.config.run.calc_type:<17}" + (f" needs {', '.join(deps)}" if deps else ""))
    for path in removed:
        _warn(f"removed stale generated config {display_path(path)}")
    print(f"\n{len(planned)} run configs written to {display_path(out)} (overview: {display_path(out / 'plan.csv')})")
    print(f"Next: hsol prepare {display_path(out)}")
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    from .run_bootstrap import PrepareError, prepare_run
    from .structures import StructureError

    site = _site()
    paths = _configs(args.configs)
    failed = 0
    for path in paths:
        try:
            result = prepare_run(path, site)
        except (PrepareError, ConfigValidationError, StructureError) as exc:
            failed += 1
            _fail(f"{path.stem}: {exc}")
            continue
        _ok(f"{result.run_id}: {result.action} -> {display_path(result.run_dir)}")
        for w in result.warnings:
            _warn(f"{result.run_id}: {w}")
    _refresh_index(site)
    return _summary(len(paths), failed, "prepare")


def cmd_run(args: argparse.Namespace) -> int:
    from .pipeline import run_pipeline

    site = _site()
    paths = _configs(args.configs)
    batch_log_dir().mkdir(parents=True, exist_ok=True)
    summary_path = batch_log_dir() / f"{utc_stamp()}_{args.mode}.tsv"
    failed = 0
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["run_id", "mode", "ok", "message", "job_id", "session_log"])
        for path in paths:
            try:
                result = run_pipeline(path, args.mode, site, resubmit=args.resubmit, echo=args.verbose)
            except ConfigValidationError as exc:
                failed += 1
                _fail(str(exc))
                continue
            session = display_path(result.session_dir) if result.session_dir else ""
            writer.writerow([result.run_id, args.mode, result.ok, result.message, result.job_id or "", session])
            if result.ok:
                _ok(f"{result.run_id}: {result.message}")
                for w in result.warnings:
                    _warn(f"{result.run_id}: {w}")
            else:
                failed += 1
                _fail(f"{result.run_id}: {result.message}" + (f"  (log: {session})" if session else ""))
                if args.stop_on_error:
                    break
    print(f"Batch log: {display_path(summary_path)}")
    if args.mode == "submit":
        _refresh_index(site)
    return _summary(len(paths), failed, f"run --mode {args.mode}")


def cmd_collect(args: argparse.Namespace) -> int:
    from .results_index import collect_run, list_run_dirs
    from .run_bootstrap import run_dir_for

    site = _site()
    run_dirs = [run_dir_for(r, site) for r in args.runs] if args.runs else list_run_dirs(site)
    failed = 0
    for run_dir in run_dirs:
        try:
            metrics = collect_run(run_dir)
        except (FileNotFoundError, ValueError) as exc:
            failed += 1
            _fail(f"{run_dir.name}: {exc}")
            continue
        if args.quiet:
            continue
        status = metrics["status"]
        detail = "; ".join(metrics.get("problems", []) + metrics.get("warnings", []))
        (_ok if status == "converged" else _warn)(f"{run_dir.name}: {status}" + (f" - {detail}" if detail else ""))
    paths = _refresh_index(site)
    if not args.quiet and paths:
        print(f"Index: {display_path(paths['markdown'])}")
    return 1 if failed else 0


def cmd_status(args: argparse.Namespace) -> int:
    from .results_index import format_status_table, index_rows, write_index

    site = _site()
    rows = index_rows(site, query_queue=not args.no_queue)
    if not rows:
        print("No runs yet. Start with: hsol plan configs/campaigns/stage1_convergence.yaml")
        return 0
    if args.stage:
        rows = [r for r in rows if r.values["stage"] == args.stage]
    print(format_status_table(rows))
    paths = write_index(index_rows(site, query_queue=False) if args.stage else rows)
    print(f"\nIndex written: {display_path(paths['markdown'])}, {display_path(paths['csv'])}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    site = _site()
    try:
        if args.what == "convergence":
            from . import convergence

            summary, _ = convergence.run(site, tolerance_meV=args.tolerance)
        else:
            from . import solubility

            summary = solubility.run(
                site, tag=args.tag, t_min=args.t_min, t_max=args.t_max, t_step=args.t_step, pressures=args.pressure_pa
            )
    except RuntimeError as exc:
        _fail(str(exc))
        return 1
    print(summary.read_text(encoding="utf-8"))
    _ok(f"written to {display_path(summary.parent)}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check everything a first run needs and say how to fix what is missing."""

    problems = 0
    py = sys.version_info
    (_ok if py >= (3, 9) else _fail)(f"Python {py.major}.{py.minor}.{py.micro} ({sys.executable})")
    problems += py < (3, 9)
    for module, required in (("yaml", True), ("pydantic", True), ("matplotlib", False)):
        if importlib.util.find_spec(module):
            _ok(f"python package '{module}'")
        elif required:
            problems += 1
            _fail(f"python package '{module}' missing: pip install -r requirements.txt")
        else:
            _warn(f"optional package '{module}' missing: analysis plots will be skipped")

    site_path = site_config_path()
    if not site_path.exists():
        problems += 1
        example, target = display_path(SITE_EXAMPLE_PATH), display_path(site_path)
        _fail(f"{target} missing: cp {example} {target} and edit it")
        site = SiteConfig()
    else:
        try:
            site = load_site_config()
            _ok(f"site config {display_path(site_path)}")
        except ConfigValidationError as exc:
            _fail(str(exc))
            return 1
        for name in site.placeholder_fields():
            problems += 1
            _fail(f"site setting {name} is still a placeholder")
    root = site.vasp.potcar_root
    if not root:
        problems += 1
        _fail("vasp.potcar_root not set in the site config (folder with Y_sv/, Zr_sv/, H/ POTCARs)")
    else:
        root_path = resolve_repo_path(root)
        for label in ("Y_sv", "Zr_sv", "H"):
            ok = (root_path / label / "POTCAR").is_file()
            problems += not ok
            (_ok if ok else _fail)(f"POTCAR {root_path / label / 'POTCAR'}")
    for tool in ("sbatch", "squeue"):
        (_ok if shutil.which(tool) else _warn)(
            f"{tool} {'found' if shutil.which(tool) else 'not found (only needed on the cluster)'}"
        )
    has_module = subprocess.run(["bash", "-lc", "type module"], capture_output=True, check=False).returncode == 0
    (_ok if has_module else _warn)(
        "environment modules " + ("available" if has_module else "not available in a login shell")
    )
    if site.environment.modules:
        print(
            "     modules to load: "
            + ", ".join(site.environment.modules)
            + "  (unsure? run tools/hpc/discover_vasp_modules.sh)"
        )
    print(
        "\n"
        + (
            "Everything needed for smoke/submit is in place."
            if not problems
            else f"{problems} problem(s) to fix before smoke/submit (plan/prepare/dryrun work regardless)."
        )
    )
    return 1 if problems else 0


# ------------------------------------------------------------------------------ parser


def _refresh_index(site: SiteConfig) -> Optional[dict]:
    from .results_index import index_rows, write_index

    try:
        return write_index(index_rows(site, query_queue=False))
    except OSError as exc:
        _warn(f"could not write results index: {exc}")
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hsol",
        description="DFT workflow for hydrogen solubility in alpha-Y vs alpha-Zr (see docs/workflow.md).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Order of work: doctor -> plan -> prepare -> run dryrun -> run smoke -> run submit\n"
        "               -> status / collect -> analyze",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    def add(name: str, func: Callable[[argparse.Namespace], int], help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.set_defaults(func=func)
        return p

    add("doctor", cmd_doctor, "check Python packages, site config, POTCARs and Slurm tools")

    p = add("plan", cmd_plan, "expand a campaign file into run configs under configs/generated/")
    p.add_argument("campaign", help="campaign file, e.g. configs/campaigns/stage1_convergence.yaml")
    p.add_argument("--output-dir", help="override the output directory")

    p = add("validate", cmd_validate, "validate run config files")
    p.add_argument("configs", nargs="+", help="config files or directories")

    p = add("prepare", cmd_prepare, "create run directories with INCAR/KPOINTS/POSCAR/POTCAR and provenance")
    p.add_argument("configs", nargs="+", help="config files or directories")

    p = add("run", cmd_run, "dryrun, smoke-test or submit runs to Slurm (in that order)")
    p.add_argument("--mode", required=True, choices=("dryrun", "smoke", "submit"))
    p.add_argument("configs", nargs="+", help="config files or directories")
    p.add_argument("--resubmit", action="store_true", help="archive raw/ of an already submitted run and submit again")
    p.add_argument("--stop-on-error", action="store_true", help="stop at the first failing run")
    p.add_argument("--verbose", action="store_true", help="print the full pipeline log for each run")

    p = add("collect", cmd_collect, "parse VASP outputs into metrics.json/report.html and refresh the index")
    p.add_argument("runs", nargs="*", help="run_ids (default: all runs)")
    p.add_argument("--quiet", action="store_true", help="only report failures (used inside Slurm jobs)")

    p = add("status", cmd_status, "show all runs and write results/INDEX.md + results/index.csv")
    p.add_argument("--stage", help="only show one stage, e.g. stage1")
    p.add_argument("--no-queue", action="store_true", help="do not query squeue")

    p = add("analyze", cmd_analyze, "analyse collected results")
    p.add_argument("what", choices=("convergence", "solubility"))
    p.add_argument("--tolerance", type=float, default=1.0, help="convergence tolerance in meV/atom (default 1)")
    p.add_argument("--tag", help="prefer runs whose run_id ends with _<tag>")
    p.add_argument("--t-min", type=float, default=300.0)
    p.add_argument("--t-max", type=float, default=1200.0)
    p.add_argument("--t-step", type=float, default=50.0)
    p.add_argument(
        "--pressure-pa",
        type=float,
        nargs="+",
        default=[1.0e5],
        help="H2 pressures for the dilute-solubility curves (default 1e5 Pa)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except ConfigValidationError as exc:
        _fail(str(exc))
        return 1
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:  # e.g. `hsol status | head`
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
