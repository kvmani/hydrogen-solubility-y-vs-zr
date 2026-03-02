#!/usr/bin/env python3
"""Append orchestration events to a run manifest and optionally update HPC submission metadata."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


def _maybe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return payload


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Append an execution event to results/runs/<run_id>/manifest.json and optionally update "
            "hpc submission metadata."
        )
    )
    parser.add_argument("--run-dir", required=True, help="Run directory containing manifest.json")
    parser.add_argument("--event", required=True, help="Event label, e.g., preflight_ok, submit_ok")
    parser.add_argument("--status", default="ok", help="Status label, e.g., ok, warn, failed")
    parser.add_argument("--mode", default=None, help="Pipeline mode: dryrun|smoke|submit")
    parser.add_argument("--message", default=None, help="Human-readable event message")
    parser.add_argument("--log-path", default=None, help="Path to pipeline/session log")
    parser.add_argument("--sbatch-script", default=None, help="Path to rendered sbatch script")
    parser.add_argument("--submit-command", default=None, help="Submission command line used")
    parser.add_argument("--scheduler-output", default=None, help="Raw scheduler stdout/stderr text")
    parser.add_argument("--job-id", default=None, help="Scheduler job id")
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    manifest_path = run_dir / "manifest.json"
    repo_root = _repo_root(run_dir)

    payload = _load_manifest(manifest_path)
    payload.setdefault("run_id", run_dir.name)

    event: dict[str, Any] = {
        "timestamp_utc": _utc_now(),
        "event": args.event,
        "status": args.status,
    }
    if args.mode:
        event["mode"] = args.mode
    if args.message:
        event["message"] = args.message

    if args.log_path:
        event["log_path"] = _maybe_rel(Path(args.log_path), repo_root)
    if args.sbatch_script:
        event["sbatch_script"] = _maybe_rel(Path(args.sbatch_script), repo_root)
    if args.submit_command:
        event["submit_command"] = args.submit_command
    if args.scheduler_output:
        event["scheduler_output"] = args.scheduler_output
    if args.job_id:
        event["job_id"] = str(args.job_id)

    events = payload.setdefault("execution_events", [])
    if not isinstance(events, list):
        raise ValueError("manifest field 'execution_events' must be a list when present")
    events.append(event)

    hpc = payload.setdefault("hpc", {})
    if not isinstance(hpc, dict):
        raise ValueError("manifest field 'hpc' must be an object when present")

    if args.job_id:
        hpc["job_id"] = str(args.job_id)

    submission = hpc.setdefault("submission", {})
    if not isinstance(submission, dict):
        raise ValueError("manifest field hpc.submission must be an object when present")

    if args.sbatch_script:
        submission["sbatch_script"] = _maybe_rel(Path(args.sbatch_script), repo_root)
    if args.submit_command:
        submission["submit_command"] = args.submit_command
    if args.scheduler_output:
        submission["scheduler_output"] = args.scheduler_output
        submission["submission_recorded_utc"] = _utc_now()
    if args.log_path:
        submission["pipeline_log"] = _maybe_rel(Path(args.log_path), repo_root)

    payload["last_update_utc"] = _utc_now()

    _write_manifest(manifest_path, payload)
    print(f"[OK] manifest updated: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
