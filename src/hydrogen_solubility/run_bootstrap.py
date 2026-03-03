"""Run-directory bootstrap helpers for config-driven workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .__version__ import __version__
from .config_models import Stage1HostConfig, load_stage1_host_config
from .pipeline import write_manifest, write_metrics, write_report

RUN_SUBDIRS = ("inputs", "logs", "raw", "parsed")


class RunInitializationError(RuntimeError):
    """Raised when run bootstrap fails."""


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


def _maybe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def _git_metadata(repo_root: Path) -> dict[str, Any]:
    commit = "unknown"
    dirty: bool | None = None

    try:
        commit_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        commit = commit_proc.stdout.strip() or "unknown"
    except (subprocess.SubprocessError, OSError):
        pass

    try:
        dirty_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        dirty = bool(dirty_proc.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        pass

    return {"commit": commit, "dirty": dirty}


def _manifest_payload(
    config: Stage1HostConfig,
    config_path: Path,
    run_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    git = _git_metadata(repo_root)

    kmesh = ",".join(str(v) for v in config.vasp.kpoints_grid)
    smearing = f"ISMEAR={config.vasp.ismear};SIGMA={config.vasp.sigma_eV}"

    return {
        "run_id": config.run.run_id,
        "timestamp_utc": timestamp,
        "stage": config.run.stage,
        "system": config.run.system,
        "objective": config.run.objective,
        "code": {
            "engine": "VASP",
            "version": "unknown",
            "workflow_version": __version__,
        },
        "git": git,
        "inputs": {
            "config_path": _maybe_rel(config_path, repo_root),
            "functional": config.vasp.functional,
            "potcar_labels": config.provenance.potcar_labels,
            "encut_eV": config.vasp.encut_eV,
            "kmesh": kmesh,
            "smearing": smearing,
        },
        "hpc": {
            "scheduler": config.hpc.scheduler,
            "job_id": None,
            "nodes": config.hpc.nodes,
            "ntasks": config.hpc.ntasks,
            "walltime": config.hpc.walltime,
            "partition": config.hpc.partition,
            "account": config.hpc.account,
        },
        "paths": {
            "run_dir": _maybe_rel(run_dir, repo_root),
            "raw_dir": _maybe_rel(run_dir / "raw", repo_root),
            "parsed_dir": _maybe_rel(run_dir / "parsed", repo_root),
        },
    }


def _metrics_payload(config: Stage1HostConfig) -> dict[str, Any]:
    return {
        "run_id": config.run.run_id,
        "status": "initialized",
        "energetics": {
            "total_energy_eV": None,
            "energy_per_atom_eV": None,
            "formation_energy_eV": None,
            "h_solution_energy_eV": None,
        },
        "checks": {
            "electronic_converged": None,
            "ionic_converged": None,
            "encut_converged": None,
            "kmesh_converged": None,
        },
        "artifacts": {
            "outcar": "raw/OUTCAR",
            "oszicar": "raw/OSZICAR",
            "summary_table": "parsed/summary.csv",
        },
        "notes": "Initialized by tools/init_run.py",
    }


def _ensure_run_dir_state(run_dir: Path, force: bool) -> None:
    if not run_dir.exists():
        return

    if not force and any(run_dir.iterdir()):
        raise RunInitializationError(
            f"Run directory already exists and is non-empty: {run_dir}. Use --force to overwrite "
            "manifest/metrics and config snapshot."
        )


def init_run_from_config(
    config_path: str | Path,
    *,
    results_root: str | Path | None = None,
    force: bool = False,
) -> dict[str, str]:
    """Create run directory structure and starter artifacts from a config."""

    config_file = Path(config_path).expanduser().resolve()
    config = load_stage1_host_config(config_file)

    repo_root = _find_repo_root(Path.cwd().resolve())
    root = Path(results_root).expanduser().resolve() if results_root else (repo_root / config.outputs.results_root)
    run_dir = root / config.run.run_id

    _ensure_run_dir_state(run_dir, force=force)

    run_dir.mkdir(parents=True, exist_ok=True)
    for subdir in RUN_SUBDIRS:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    snapshot_path = run_dir / "inputs" / f"config_snapshot{config_file.suffix.lower() or '.yaml'}"
    shutil.copy2(config_file, snapshot_path)

    manifest_payload = _manifest_payload(config=config, config_path=config_file, run_dir=run_dir, repo_root=repo_root)
    metrics_payload = _metrics_payload(config)

    if config.outputs.write_manifest or force:
        write_manifest(str(run_dir), manifest_payload)
    if config.outputs.write_metrics or force:
        write_metrics(str(run_dir), metrics_payload)
    if config.outputs.write_report_html or force:
        write_report(str(run_dir), manifest_payload=manifest_payload, metrics_payload=metrics_payload)

    return {
        "run_id": config.run.run_id,
        "run_dir": str(run_dir),
        "manifest": str(run_dir / "manifest.json"),
        "metrics": str(run_dir / "metrics.json"),
        "report": str(run_dir / "report.html"),
        "config_snapshot": str(snapshot_path),
    }
