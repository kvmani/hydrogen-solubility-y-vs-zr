#!/usr/bin/env python3
"""Audit and optionally patch scheduler placeholders in stage-1 config files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any

import yaml
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from hydrogen_solubility.config_models import Stage1HostConfig  # noqa: E402


PLACEHOLDER_TOKENS = {"", "placeholder", "replace_me", "tbd", "todo"}
SUPPORTED_SUFFIXES = {".yaml", ".yml", ".json"}
DIRECTORY_SCAN_SUFFIXES = {".yaml", ".yml"}


@dataclass
class AuditResult:
    path: Path
    valid: bool
    validation_error: str
    partition: str
    account: str
    partition_is_placeholder: bool
    account_is_placeholder: bool
    patched_partition: bool
    patched_account: bool
    wrote_file: bool


class ConfigError(ValueError):
    """Raised when a candidate config cannot be loaded."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit one or many stage-1 config files for scheduler readiness and optionally patch "
            "hpc.partition/hpc.account in place."
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
        "--set-partition",
        default=None,
        help="Replacement value for hpc.partition.",
    )
    parser.add_argument(
        "--set-account",
        default=None,
        help="Replacement value for hpc.account.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persist patched scheduler values to disk (default: audit-only).",
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
        "--patch-all",
        action="store_true",
        help="Patch scheduler fields even if they are not placeholders.",
    )
    parser.add_argument(
        "--fail-if-unready",
        action="store_true",
        help="Exit non-zero when any config is invalid or still has scheduler placeholders.",
    )
    return parser


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True

    text = str(value).strip()
    lowered = text.lower()

    if text.startswith("<") and text.endswith(">"):
        return True
    if "<" in text or ">" in text:
        return True
    if lowered in PLACEHOLDER_TOKENS:
        return True

    return False


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


def _load_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    try:
        if suffix in {".yaml", ".yml"}:
            payload = yaml.safe_load(text)
        elif suffix == ".json":
            payload = json.loads(text)
        else:
            raise ConfigError(f"Unsupported config extension: {path}")
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Failed to parse {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ConfigError(f"Top-level config payload must be an object: {path}")

    return payload


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        rendered = yaml.safe_dump(payload, sort_keys=False)
    elif suffix == ".json":
        rendered = json.dumps(payload, indent=2)
        if not rendered.endswith("\n"):
            rendered += "\n"
    else:
        raise ConfigError(f"Unsupported config extension for write: {path}")

    path.write_text(rendered, encoding="utf-8")


def _audit_one(
    path: Path,
    *,
    set_partition: str | None,
    set_account: str | None,
    patch_all: bool,
    write: bool,
) -> AuditResult:
    payload = _load_payload(path)

    hpc_section = payload.get("hpc")
    if not isinstance(hpc_section, dict):
        raise ConfigError(f"Missing or invalid hpc section: {path}")

    partition_raw = str(hpc_section.get("partition", "")).strip()
    account_raw = str(hpc_section.get("account", "")).strip()

    partition_is_placeholder = _is_placeholder(partition_raw)
    account_is_placeholder = _is_placeholder(account_raw)

    patched_partition = False
    patched_account = False

    if set_partition is not None:
        should_patch_partition = patch_all or partition_is_placeholder
        if should_patch_partition and partition_raw != set_partition:
            hpc_section["partition"] = set_partition
            patched_partition = True

    if set_account is not None:
        should_patch_account = patch_all or account_is_placeholder
        if should_patch_account and account_raw != set_account:
            hpc_section["account"] = set_account
            patched_account = True

    wrote_file = False
    if write and (patched_partition or patched_account):
        _write_payload(path, payload)
        wrote_file = True

    final_partition = str(hpc_section.get("partition", "")).strip()
    final_account = str(hpc_section.get("account", "")).strip()

    try:
        Stage1HostConfig.model_validate(payload)
        valid = True
        validation_error = ""
    except ValidationError as exc:
        valid = False
        validation_error = str(exc).replace("\n", " ")

    return AuditResult(
        path=path,
        valid=valid,
        validation_error=validation_error,
        partition=final_partition,
        account=final_account,
        partition_is_placeholder=_is_placeholder(final_partition),
        account_is_placeholder=_is_placeholder(final_account),
        patched_partition=patched_partition,
        patched_account=patched_account,
        wrote_file=wrote_file,
    )


def _print_results(results: list[AuditResult]) -> None:
    for item in results:
        status = "READY" if item.valid and not item.partition_is_placeholder and not item.account_is_placeholder else "UNREADY"
        patch_notes = []
        if item.patched_partition:
            patch_notes.append("partition")
        if item.patched_account:
            patch_notes.append("account")
        patch_str = ",".join(patch_notes) if patch_notes else "-"

        print(
            f"[{status}] {_relative(item.path)} | "
            f"partition={item.partition!r} placeholder={item.partition_is_placeholder} | "
            f"account={item.account!r} placeholder={item.account_is_placeholder} | "
            f"patched={patch_str} | wrote={item.wrote_file}"
        )
        if not item.valid:
            print(f"  validation_error: {item.validation_error}")

    total = len(results)
    ready = sum(1 for r in results if r.valid and not r.partition_is_placeholder and not r.account_is_placeholder)
    invalid = sum(1 for r in results if not r.valid)
    unresolved = sum(1 for r in results if r.partition_is_placeholder or r.account_is_placeholder)
    patched = sum(1 for r in results if r.patched_partition or r.patched_account)
    written = sum(1 for r in results if r.wrote_file)

    print(
        "SUMMARY "
        f"total={total} ready={ready} invalid={invalid} unresolved_placeholders={unresolved} "
        f"patched={patched} files_written={written}"
    )


def main() -> int:
    args = _build_parser().parse_args()
    recursive = True
    if args.no_recursive:
        recursive = False
    if args.recursive:
        recursive = True

    if args.write and args.set_partition is None and args.set_account is None:
        print("ERROR: --write requires --set-partition and/or --set-account.", file=sys.stderr)
        return 2

    if args.set_partition is not None and _is_placeholder(args.set_partition):
        print("ERROR: --set-partition still looks like a placeholder.", file=sys.stderr)
        return 2

    if args.set_account is not None and _is_placeholder(args.set_account):
        print("ERROR: --set-account still looks like a placeholder.", file=sys.stderr)
        return 2

    try:
        paths = _collect_paths(args.paths, recursive=recursive)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not paths:
        print("ERROR: no supported config files found.", file=sys.stderr)
        return 2

    results: list[AuditResult] = []
    for path in paths:
        try:
            result = _audit_one(
                path,
                set_partition=args.set_partition,
                set_account=args.set_account,
                patch_all=args.patch_all,
                write=args.write,
            )
        except ConfigError as exc:
            results.append(
                AuditResult(
                    path=path,
                    valid=False,
                    validation_error=str(exc),
                    partition="",
                    account="",
                    partition_is_placeholder=True,
                    account_is_placeholder=True,
                    patched_partition=False,
                    patched_account=False,
                    wrote_file=False,
                )
            )
            continue

        results.append(result)

    _print_results(results)

    unready = any(not r.valid or r.partition_is_placeholder or r.account_is_placeholder for r in results)
    if args.fail_if_unready and unready:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
