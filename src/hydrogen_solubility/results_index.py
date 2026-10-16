"""``hsol collect`` and ``hsol status``: parse finished runs and keep an index of all runs.

``collect`` turns raw VASP outputs into ``metrics.json`` (plus calc-type specific
structure checks), stamps the VASP version into the manifest and refreshes
``report.html``. It is safe to run repeatedly: an event is only logged when the
parsed status or energy changes.

``build_index`` writes two overview files that make results discoverable:

* ``results/index.csv`` -- one row per run, for scripts and spreadsheets;
* ``results/INDEX.md``  -- the same, grouped by stage, with links to each
  ``report.html`` (renders nicely on GitHub).
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import structures as st
from .config_models import SiteConfig
from .paths import results_dir
from .provenance import append_event, read_json, utc_now, write_json
from .reporting import write_run_report
from .run_bootstrap import load_config_for_run, results_root
from .vasp_metrics import build_metrics_payload

INDEX_COLUMNS = (
    "run_id",
    "stage",
    "system",
    "calc_type",
    "status",
    "queue",
    "energy_sigma0_eV",
    "energy_per_atom_eV",
    "natoms",
    "job_id",
    "problems",
    "last_update_utc",
)
STAGE_TITLES = {
    "stage1": "Stage 1 - host convergence and lattice relaxation",
    "stage2": "Stage 2 - H interstitials and H2 reference",
    "stage3": "Stage 3 - vibrations (zero-point energy)",
    "stage4": "Stage 4 - hydride competition",
}


# ---------------------------------------------------------------------------- collect


def _structure_checks(calc_type: str, contcar: Path, requested_site: Optional[str]) -> Dict[str, Any]:
    """Calc-type specific checks of the relaxed structure (empty if CONTCAR missing)."""

    if not contcar.is_file() or contcar.stat().st_size == 0:
        return {}
    try:
        final = st.Structure.read(contcar)
    except st.StructureError as exc:
        return {"error": str(exc)}
    checks: Dict[str, Any] = {"volume_per_atom_A3": round(final.volume / final.natoms, 5)}
    if calc_type == "host_relax":
        try:
            a, c = st.hcp_lattice_parameters(final)
            checks.update({"a_A": round(a, 5), "c_A": round(c, 5), "c_over_a": round(c / a, 5)})
        except st.StructureError as exc:
            checks["error"] = str(exc)
    elif calc_type == "hydride_relax":
        checks["cell_lengths_A"] = [round(x, 5) for x in final.lengths()]
    elif calc_type == "h_interstitial":
        site = st.classify_h_site(final)
        checks.update({"requested_site": requested_site, "final_site": site, "site_preserved": site == requested_site})
    return checks


def collect_run(run_dir: Path) -> Dict[str, Any]:
    """Parse one run directory and update its metrics, manifest and report."""

    manifest = read_json(run_dir / "manifest.json")
    if not manifest:
        raise FileNotFoundError(f"{run_dir} has no manifest.json (not a prepared run)")
    config = load_config_for_run(run_dir)
    calc_type = manifest.get("calc_type", "unknown")
    previous = read_json(run_dir / "metrics.json")

    raw = run_dir / "raw"
    metrics = build_metrics_payload(
        run_id=manifest["run_id"], calc_type=calc_type, outcar_path=raw / "OUTCAR", oszicar_path=raw / "OSZICAR"
    )
    if metrics["status"] == "not_started" and previous.get("status") in ("prepared", "submitted"):
        # Nothing ran yet: keep the workflow status rather than reporting an error.
        metrics["status"] = previous["status"]
        metrics["problems"] = []

    warnings: List[str] = []
    requested_site = config.structure.h_site if config else None
    checks = _structure_checks(calc_type, raw / "CONTCAR", requested_site)
    if checks:
        metrics["structure_check"] = checks
        if calc_type == "h_interstitial" and checks.get("site_preserved") is False:
            warnings.append(
                f"H started in the {requested_site} site but ended in '{checks.get('final_site')}': "
                "the starting site is probably not a local minimum."
            )
    vib = metrics.get("vibrations")
    if vib and manifest.get("system") == "H2":
        # A free molecule has 5 near-zero translation/rotation modes that finite
        # differences may report as small imaginary values; only the stretch matters.
        stretch = max(vib["modes"], key=lambda m: m["meV"])
        if stretch["imaginary"]:
            warnings.append("the H2 stretching mode is imaginary: check the H2 relaxation.")
    elif vib and vib["n_imaginary"]:
        warnings.append(f"{vib['n_imaginary']} imaginary mode(s): the structure is not a local minimum.")
    metrics["warnings"] = warnings
    metrics["collected_utc"] = utc_now()
    write_json(run_dir / "metrics.json", metrics)

    version = (metrics.get("calculation") or {}).get("vasp_version")
    changed = (previous.get("status"), (previous.get("energetics") or {}).get("energy_sigma0_eV")) != (
        metrics["status"],
        metrics["energetics"]["energy_sigma0_eV"],
    )
    if changed:
        append_event(
            run_dir,
            "collected",
            "ok" if metrics["status"] == "converged" else "warn",
            f"status={metrics['status']}" + (f"; {'; '.join(metrics['problems'])}" if metrics["problems"] else ""),
            updates={"vasp": {"version": version}} if version else None,
        )
    write_run_report(run_dir)
    return metrics


# ----------------------------------------------------------------------------- index


@dataclass
class RunRow:
    values: Dict[str, Any]
    run_dir: Path


def list_run_dirs(site: SiteConfig) -> List[Path]:
    root = results_root(site)
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if (p / "manifest.json").is_file())


def queue_states(job_ids: List[str]) -> Optional[Dict[str, str]]:
    """Slurm states of queued/running jobs via ``squeue``; ``None`` if Slurm is unavailable.

    Jobs absent from the result have left the queue (finished, failed or cancelled).
    """

    if not job_ids or not shutil.which("squeue"):
        return None
    try:
        proc = subprocess.run(
            ["squeue", "-h", "-j", ",".join(job_ids), "-o", "%i %T"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    states = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2:
            states[parts[0]] = parts[1]
    return states


def index_rows(site: SiteConfig, *, query_queue: bool = True) -> List[RunRow]:
    rows = []
    for run_dir in list_run_dirs(site):
        manifest = read_json(run_dir / "manifest.json")
        metrics = read_json(run_dir / "metrics.json")
        energetics = metrics.get("energetics") or {}
        values = {
            "run_id": manifest.get("run_id", run_dir.name),
            "stage": manifest.get("stage"),
            "system": manifest.get("system"),
            "calc_type": manifest.get("calc_type"),
            "status": metrics.get("status", "unknown"),
            "queue": "",
            "energy_sigma0_eV": energetics.get("energy_sigma0_eV"),
            "energy_per_atom_eV": energetics.get("energy_per_atom_eV"),
            "natoms": (manifest.get("structure") or {}).get("natoms"),
            "job_id": (manifest.get("hpc") or {}).get("job_id"),
            "problems": len(metrics.get("problems") or []) + len(metrics.get("warnings") or []),
            "last_update_utc": manifest.get("last_update_utc"),
        }
        rows.append(RunRow(values, run_dir))
    if query_queue:
        pending = [str(r.values["job_id"]) for r in rows if r.values["job_id"] and r.values["status"] == "submitted"]
        states = queue_states(pending)
        if states is not None:
            for r in rows:
                if r.values["status"] == "submitted" and r.values["job_id"]:
                    r.values["queue"] = states.get(str(r.values["job_id"]), "left queue - run hsol collect")
    return rows


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def write_index(rows: List[RunRow], output_dir: Optional[Path] = None) -> Dict[str, Path]:
    """Write ``index.csv`` and ``INDEX.md`` into ``output_dir`` (default: the results workspace)."""

    out = output_dir or results_dir()
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "index.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _fmt(row.values.get(k)) for k in INDEX_COLUMNS})

    md_path = out / "INDEX.md"
    counts: Dict[str, int] = {}
    for row in rows:
        counts[row.values["status"]] = counts.get(row.values["status"], 0) + 1
    lines = [
        "# Results index",
        "",
        f"Generated by `hsol status` at {utc_now()}. Do not edit by hand.",
        "",
        "Totals: " + (", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "no runs yet"),
        "",
    ]
    for stage in sorted({r.values["stage"] or "unknown" for r in rows}):
        lines += [
            f"## {STAGE_TITLES.get(stage, stage)}",
            "",
            "| Run | Calculation | Status | E0 / atom (eV) | Atoms | Issues |",
            "|---|---|---|---|---|---|",
        ]
        for row in (r for r in rows if (r.values["stage"] or "unknown") == stage):
            v = row.values
            link = os.path.relpath(row.run_dir / "report.html", out)
            status = v["status"] + (f" ({v['queue']})" if v["queue"] else "")
            lines.append(
                f"| [{v['run_id']}]({link}) | {v['calc_type']} | {status} | {_fmt(v['energy_per_atom_eV'])} "
                f"| {_fmt(v['natoms'])} | {v['problems'] or ''} |"
            )
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"csv": csv_path, "markdown": md_path}


def format_status_table(rows: List[RunRow]) -> str:
    """Plain-text table for the terminal."""

    headers = ("RUN", "CALC", "STATUS", "E0/ATOM (eV)", "ISSUES")
    data = [
        (
            r.values["run_id"],
            r.values["calc_type"] or "",
            r.values["status"] + (f" ({r.values['queue']})" if r.values["queue"] else ""),
            _fmt(r.values["energy_per_atom_eV"]),
            str(r.values["problems"] or ""),
        )
        for r in rows
    ]
    widths = [max(len(h), *(len(d[i]) for d in data)) if data else len(h) for i, h in enumerate(headers)]
    out = ["  ".join(h.ljust(w) for h, w in zip(headers, widths))]
    out += ["  ".join(c.ljust(w) for c, w in zip(d, widths)) for d in data]
    return "\n".join(out)


def find_runs(
    site: SiteConfig, *, calc_type: str, system: Optional[str] = None, **structure_filters: Any
) -> List[Path]:
    """Run directories matching calc type, system and (optional) config.structure fields."""

    matches = []
    for run_dir in list_run_dirs(site):
        manifest = read_json(run_dir / "manifest.json")
        if manifest.get("calc_type") != calc_type or (system and manifest.get("system") != system):
            continue
        if structure_filters:
            config = load_config_for_run(run_dir)
            if config is None or any(getattr(config.structure, k) != v for k, v in structure_filters.items()):
                continue
        matches.append(run_dir)
    return matches
