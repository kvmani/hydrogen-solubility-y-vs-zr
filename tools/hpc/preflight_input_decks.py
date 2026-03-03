#!/usr/bin/env python3
"""Audit run input deck completeness for one or many stage-1 config files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from hydrogen_solubility.config_models import ConfigValidationError, load_stage1_host_config  # noqa: E402
from hydrogen_solubility.run_bootstrap import RunInitializationError, init_run_from_config  # noqa: E402

SUPPORTED_SUFFIXES = {".yaml", ".yml", ".json"}
DIRECTORY_SCAN_SUFFIXES = {".yaml", ".yml"}


@dataclass
class InputAuditResult:
    path: Path
    run_id: str
    run_dir: Path | None
    input_dir: Path | None
    valid_config: bool
    config_error: str
    initialized: bool
    init_error: str
    required_files: list[str]
    missing_files: list[str]


class ConfigError(ValueError):
    """Raised when path collection or config loading fails."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit stage-1 run input deck completeness under results/runs/<run_id>/inputs for one or many configs."
        )
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "Config files or directories. Directories are scanned recursively for .yaml/.yml by default; "
            "JSON can still be passed explicitly as a file path. Shell globs are also supported."
        ),
    )
    parser.add_argument(
        "--require-potcar",
        choices=("true", "false"),
        default="true",
        help="Whether POTCAR is required in inputs/ (default: true).",
    )
    parser.add_argument(
        "--results-root",
        default=None,
        help="Optional override for outputs.results_root across all configs.",
    )
    parser.add_argument(
        "--inputs-subdir",
        default="inputs",
        help="Input deck subdirectory inside each run directory (default: inputs).",
    )
    parser.add_argument(
        "--init-if-missing",
        action="store_true",
        help="Initialize missing run directories via tools/init_run.py logic before checking inputs.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into input directories (default: true).",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Disable recursive directory scanning.",
    )
    parser.add_argument(
        "--fail-if-unready",
        action="store_true",
        help="Exit non-zero when any config is invalid, missing run dir, or missing required input files.",
    )
    return parser


def _collect_paths(inputs: list[str], *, recursive: bool) -> list[Path]:
    candidates: set[Path] = set()

    for raw in inputs:
        expanded = Path(raw).expanduser()
        pattern_chars = {"*", "?", "["}
        if any(ch in raw for ch in pattern_chars):
            for match in sorted(Path.cwd().glob(raw)):
                if match.is_file() and match.suffix.lower() in SUPPORTED_SUFFIXES:
                    candidates.add(match.resolve())
            continue

        if not expanded.exists():
            raise ConfigError(f"Path not found: {raw}")

        resolved = expanded.resolve()
        if resolved.is_file():
            if resolved.suffix.lower() in SUPPORTED_SUFFIXES:
                candidates.add(resolved)
            continue

        if resolved.is_dir():
            iterator = resolved.rglob("*") if recursive else resolved.glob("*")
            for child in iterator:
                if child.is_file() and child.suffix.lower() in DIRECTORY_SCAN_SUFFIXES:
                    candidates.add(child.resolve())
            continue

        raise ConfigError(f"Unsupported path type: {raw}")

    return sorted(candidates)


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _resolve_results_root(raw: str | None, *, config_results_root: str) -> Path:
    token = raw if raw is not None else config_results_root
    path = Path(token).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def _required_inputs(*, require_potcar: bool) -> list[str]:
    required = ["INCAR", "POSCAR", "KPOINTS"]
    if require_potcar:
        required.append("POTCAR")
    return required


def _audit_one(
    config_path: Path,
    *,
    require_potcar: bool,
    results_root_override: str | None,
    inputs_subdir: str,
    init_if_missing: bool,
) -> InputAuditResult:
    try:
        cfg = load_stage1_host_config(config_path)
    except ConfigValidationError as exc:
        return InputAuditResult(
            path=config_path,
            run_id="-",
            run_dir=None,
            input_dir=None,
            valid_config=False,
            config_error=str(exc).replace("\n", " "),
            initialized=False,
            init_error="",
            required_files=_required_inputs(require_potcar=require_potcar),
            missing_files=_required_inputs(require_potcar=require_potcar),
        )

    run_id = cfg.run.run_id
    results_root = _resolve_results_root(results_root_override, config_results_root=cfg.outputs.results_root)
    run_dir = results_root / run_id
    input_dir = run_dir / inputs_subdir

    initialized = False
    init_error = ""
    if not run_dir.exists() and init_if_missing:
        try:
            init_run_from_config(config_path=config_path, results_root=results_root, force=False)
            initialized = True
        except (RunInitializationError, ConfigValidationError, ValueError) as exc:
            init_error = str(exc).replace("\n", " ")

    required = _required_inputs(require_potcar=require_potcar)
    missing = []
    for name in required:
        if not (input_dir / name).is_file():
            missing.append(name)

    return InputAuditResult(
        path=config_path,
        run_id=run_id,
        run_dir=run_dir,
        input_dir=input_dir,
        valid_config=True,
        config_error="",
        initialized=initialized,
        init_error=init_error,
        required_files=required,
        missing_files=missing,
    )


def _is_ready(item: InputAuditResult) -> bool:
    if not item.valid_config:
        return False
    if item.run_dir is None or item.input_dir is None:
        return False
    if item.init_error:
        return False
    if not item.run_dir.exists():
        return False
    if not item.input_dir.exists():
        return False
    return len(item.missing_files) == 0


def _print_results(results: list[InputAuditResult]) -> None:
    for item in results:
        ready = _is_ready(item)
        status = "READY" if ready else "UNREADY"
        missing = ",".join(item.missing_files) if item.missing_files else "-"

        run_dir_text = _relative(item.run_dir) if item.run_dir else "-"
        input_dir_text = _relative(item.input_dir) if item.input_dir else "-"

        print(
            f"[{status}] {_relative(item.path)} | run_id={item.run_id} | "
            f"run_dir={run_dir_text} | input_dir={input_dir_text} | "
            f"missing={missing} | initialized={item.initialized}"
        )

        if item.config_error:
            print(f"  config_error: {item.config_error}")
        if item.init_error:
            print(f"  init_error: {item.init_error}")

    total = len(results)
    ready = sum(1 for r in results if _is_ready(r))
    invalid = sum(1 for r in results if not r.valid_config)
    missing_run_dirs = sum(1 for r in results if r.run_dir is None or not r.run_dir.exists())
    missing_input_dirs = sum(1 for r in results if r.input_dir is None or not r.input_dir.exists())
    configs_with_missing_files = sum(1 for r in results if len(r.missing_files) > 0)
    missing_files_total = sum(len(r.missing_files) for r in results)
    initialized = sum(1 for r in results if r.initialized)

    print(
        "SUMMARY "
        f"total={total} ready={ready} invalid={invalid} missing_run_dirs={missing_run_dirs} "
        f"missing_input_dirs={missing_input_dirs} configs_with_missing_files={configs_with_missing_files} "
        f"missing_files_total={missing_files_total} initialized={initialized}"
    )


def main() -> int:
    args = _build_parser().parse_args()

    recursive = True
    if args.no_recursive:
        recursive = False
    if args.recursive:
        recursive = True

    require_potcar = args.require_potcar == "true"

    try:
        paths = _collect_paths(args.paths, recursive=recursive)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not paths:
        print("ERROR: no supported config files found.", file=sys.stderr)
        return 2

    results: list[InputAuditResult] = []
    for path in paths:
        result = _audit_one(
            path,
            require_potcar=require_potcar,
            results_root_override=args.results_root,
            inputs_subdir=args.inputs_subdir,
            init_if_missing=args.init_if_missing,
        )
        results.append(result)

    _print_results(results)

    unready = any(not _is_ready(item) for item in results)
    if args.fail_if_unready and unready:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
