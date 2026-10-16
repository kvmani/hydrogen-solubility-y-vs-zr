"""Provenance capture: git state, environment, file hashes and manifest events.

``manifest.json`` is the provenance record of one run (schema in
``docs/data_model.md``). It is created by ``hsol prepare`` and only ever *appended
to* afterwards: every prepare/dryrun/smoke/submit/collect action adds an entry to
``events`` so the operational history of the run is never lost.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .__version__ import __version__
from .paths import REPO_ROOT

MANIFEST_VERSION = "2.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    """Compact timestamp for file names, e.g. ``20261016T120501Z``."""

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def combined_hash(hashes: Dict[str, Optional[str]]) -> str:
    """Order-independent fingerprint of a set of named file hashes."""

    joined = "\n".join(f"{name}:{hashes[name] or '-'}" for name in sorted(hashes))
    return sha256_text(joined)


def _git(*args: str) -> Optional[str]:
    try:
        proc = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=20, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip()


def git_state() -> Dict[str, Any]:
    """Commit, branch and whether uncommitted changes exist (``dirty``)."""

    status = _git("status", "--porcelain", "--untracked-files=no")
    return {
        "commit": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": None if status is None else bool(status),
    }


def environment_state() -> Dict[str, Any]:
    return {
        "workflow_version": __version__,
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
    }


# ----------------------------------------------------------------------------- JSON IO


def read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupt JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Write JSON atomically so an interrupted write never leaves a truncated file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------- events


def append_event(
    run_dir: Path,
    event: str,
    status: str,
    message: str,
    *,
    mode: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    updates: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append one event to ``manifest.json`` and optionally merge top-level ``updates``.

    ``updates`` values that are dicts are merged one level deep (e.g.
    ``{"hpc": {"job_id": "123"}}`` keeps the other ``hpc`` keys).
    """

    manifest_path = run_dir / "manifest.json"
    manifest = read_json(manifest_path)
    if not manifest:
        raise FileNotFoundError(f"{manifest_path} does not exist; run `hsol prepare` first")
    record: Dict[str, Any] = {"timestamp_utc": utc_now(), "event": event, "status": status, "message": message}
    if mode:
        record["mode"] = mode
    if details:
        record["details"] = details
    manifest.setdefault("events", []).append(record)
    for key, value in (updates or {}).items():
        if isinstance(value, dict) and isinstance(manifest.get(key), dict):
            manifest[key].update(value)
        else:
            manifest[key] = value
    manifest["last_update_utc"] = record["timestamp_utc"]
    write_json(manifest_path, manifest)
    return record


def last_event(manifest: Dict[str, Any], names: Iterable[str]) -> Optional[Dict[str, Any]]:
    """Most recent event whose name is in ``names``."""

    wanted = set(names)
    for record in reversed(manifest.get("events", [])):
        if record.get("event") in wanted:
            return record
    return None
