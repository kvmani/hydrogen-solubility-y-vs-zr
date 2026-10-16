"""``hsol prepare``: turn a run config into a complete, provenance-tracked run directory.

Layout created under ``<results_root>/<run_id>/``::

    inputs/config.yaml   exact config snapshot
    inputs/INCAR         rendered from config.vasp.incar
    inputs/KPOINTS       rendered from config.vasp.kpoints
    inputs/POSCAR        built from config.structure (may read a parent run's CONTCAR)
    inputs/POTCAR        assembled from the site PAW library (never committed)
    raw/                 VASP working directory (inputs are copied here at submit time)
    logs/                orchestration sessions and Slurm logs
    manifest.json        provenance + event history
    metrics.json         parsed results (status "prepared" until collected)
    report.html          human-readable summary

Preparing is idempotent. Re-running it on an unchanged config does nothing; if the
config changed and VASP has not run yet, inputs are regenerated (and an event is
logged); if VASP outputs already exist for a *different* config, preparation is
refused so results can never silently lose their inputs.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import structures as st
from .config_models import RunConfig, SiteConfig, load_run_config
from .paths import display_path, resolve_repo_path
from .provenance import (
    MANIFEST_VERSION,
    append_event,
    combined_hash,
    environment_state,
    git_state,
    read_json,
    sha256_file,
    utc_now,
    write_json,
)
from .reporting import write_run_report
from .vasp_inputs import (
    PotcarError,
    assemble_potcar,
    encut_warnings,
    potcar_records_as_dicts,
    render_incar,
    render_kpoints,
)

INPUT_FILES = ("INCAR", "KPOINTS", "POSCAR", "POTCAR")


class PrepareError(RuntimeError):
    """Raised when a run cannot be prepared (missing parent results, conflicts, ...)."""


@dataclass
class PrepareResult:
    run_id: str
    run_dir: Path
    action: str  # created | regenerated | unchanged
    warnings: List[str] = field(default_factory=list)
    potcar_written: bool = False


def results_root(site: SiteConfig) -> Path:
    return resolve_repo_path(site.paths.results_root)


def run_dir_for(run_id: str, site: SiteConfig) -> Path:
    return results_root(site) / run_id


# ------------------------------------------------------------------------- structures


def _parent_contcar(parent_id: str, site: SiteConfig) -> Tuple[st.Structure, Dict[str, Any]]:
    """CONTCAR of a finished parent run, refusing parents that are not converged."""

    parent_dir = run_dir_for(parent_id, site)
    metrics = read_json(parent_dir / "metrics.json")
    status = metrics.get("status", "missing")
    if status != "converged":
        raise PrepareError(
            f"parent run '{parent_id}' must be converged before this run can be prepared "
            f"(current status: {status}). Run `hsol collect` after it finishes."
        )
    contcar = parent_dir / "raw" / "CONTCAR"
    structure = st.Structure.read(contcar)
    return structure, {"run_id": parent_id, "contcar": display_path(contcar), "sha256": sha256_file(contcar)}


def build_structure(config: RunConfig, site: SiteConfig) -> Tuple[st.Structure, Dict[str, Any]]:
    """Build the starting structure and describe where it came from."""

    s = config.structure
    element = "H" if config.run.system == "H2" else config.run.system
    info: Dict[str, Any] = {"builder": s.builder, "source": s.source, "parents": []}

    a, c = s.a_A, s.c_A
    if s.lattice_from_run:
        parent, parent_info = _parent_contcar(s.lattice_from_run, site)
        a, c = st.hcp_lattice_parameters(parent)
        info["parents"].append(parent_info)
    if a is not None:
        info["lattice_A"] = {"a": round(a, 6), "c": round(c, 6) if c is not None else None}

    if s.builder == "hcp_primitive":
        structure = st.hcp_primitive(element, a, c)  # type: ignore[arg-type]
    elif s.builder == "hcp_supercell":
        structure = st.hcp_supercell(element, a, c, s.supercell, s.h_site)  # type: ignore[arg-type]
        info["supercell"] = list(s.supercell)
        info["h_site"] = s.h_site
    elif s.builder == "h2_molecule":
        structure = st.h2_molecule(s.box_A, s.bond_A)  # type: ignore[arg-type]
    elif s.builder == "fluorite_dihydride":
        structure = st.fluorite_dihydride(element, a)  # type: ignore[arg-type]
    elif s.builder == "from_run":
        parent, parent_info = _parent_contcar(s.from_run, site)  # type: ignore[arg-type]
        structure = parent.with_free_species(s.free_species)
        info["parents"].append(parent_info)
        info["free_species"] = list(s.free_species)
    elif s.builder == "file":
        path = resolve_repo_path(s.file)  # type: ignore[arg-type]
        structure = st.Structure.read(path)
        info["file"] = {"path": display_path(path), "sha256": sha256_file(path)}
    else:  # pragma: no cover - guarded by the schema
        raise PrepareError(f"unknown builder {s.builder}")

    structure.comment = f"{config.run_id}: {structure.comment}"
    info["natoms"] = structure.natoms
    info["composition"] = {sp: structure.count(sp) for sp in structure.species_order}
    return structure, info


def resolve_kpoint_grid(config: RunConfig, structure: st.Structure) -> Tuple[int, int, int]:
    """The explicit grid, or the grid implied by ``kpoints.spacing`` for this cell."""

    k = config.vasp.kpoints
    return k.grid if k.grid is not None else st.kpoint_grid_for_spacing(structure, k.spacing)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------- prepare


def _has_vasp_outputs(run_dir: Path) -> bool:
    return (run_dir / "raw" / "OUTCAR").exists()


def _write_inputs(
    config: RunConfig, config_text: str, structure: st.Structure, site: SiteConfig, inputs_dir: Path
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Write all input files; returns (warnings, potcar records)."""

    inputs_dir.mkdir(parents=True, exist_ok=True)
    (inputs_dir / "config.yaml").write_text(config_text, encoding="utf-8")
    (inputs_dir / "INCAR").write_text(render_incar(config.vasp.incar, system_label=config.run_id), encoding="utf-8")
    grid = resolve_kpoint_grid(config, structure)
    (inputs_dir / "KPOINTS").write_text(render_kpoints(grid, config.vasp.kpoints.style), encoding="utf-8")
    (inputs_dir / "POSCAR").write_text(structure.to_poscar(), encoding="utf-8")

    warnings: List[str] = []
    missing_labels = [sp for sp in structure.species_order if sp not in config.potcars]
    if missing_labels:
        raise PrepareError(f"potcars has no label for species {missing_labels} present in the POSCAR")

    potcar_path = inputs_dir / "POTCAR"
    records: List[Dict[str, Any]] = []
    if site.vasp.potcar_root:
        try:
            text, potcars = assemble_potcar(
                resolve_repo_path(site.vasp.potcar_root), structure.species_order, config.potcars
            )
        except PotcarError as exc:
            raise PrepareError(str(exc)) from exc
        potcar_path.write_text(text, encoding="utf-8")
        records = potcar_records_as_dicts(potcars)
        incar = config.vasp.incar
        warnings += encut_warnings(float(incar["ENCUT"]), potcars, cell_relax=incar.get("ISIF") == 3)  # type: ignore[arg-type]
    else:
        if potcar_path.exists():
            potcar_path.unlink()
        warnings.append("POTCAR not written: set vasp.potcar_root in configs/site.yaml (required for smoke/submit).")
    return warnings, records


def prepare_run(config_path: Path, site: SiteConfig) -> PrepareResult:
    """Create or refresh one run directory from its config file."""

    config = load_run_config(config_path)
    config_text = config_path.read_text(encoding="utf-8")
    config_hash = config.science_hash()
    run_dir = run_dir_for(config.run_id, site)
    manifest_path = run_dir / "manifest.json"
    existing = read_json(manifest_path)

    if existing:
        same_config = existing.get("config", {}).get("sha256") == config_hash
        if same_config and all((run_dir / "inputs" / f).exists() for f in INPUT_FILES[:3]):
            potcar_ok = (run_dir / "inputs" / "POTCAR").exists()
            if potcar_ok or not site.vasp.potcar_root:
                snapshot = run_dir / "inputs" / "config.yaml"
                if snapshot.read_text(encoding="utf-8") != config_text:
                    # Only non-physics fields (hpc, objective, notes) changed.
                    snapshot.write_text(config_text, encoding="utf-8")
                    append_event(run_dir, "config_snapshot_updated", "ok", "Non-physics config fields changed.")
                return PrepareResult(config.run_id, run_dir, "unchanged", potcar_written=potcar_ok)
        if not same_config and _has_vasp_outputs(run_dir):
            raise PrepareError(
                f"{config.run_id}: VASP outputs exist for a different config. Never overwrite results - "
                "give the changed calculation a new run_id (set `tag:` in the campaign file)."
            )

    structure, structure_info = build_structure(config, site)
    grid = resolve_kpoint_grid(config, structure)
    structure_info["kpoints_grid"] = list(grid)
    structure_info["kpoint_spacing_A-1"] = round(st.kpoint_spacing_of_grid(structure, grid), 5)
    for sub in ("inputs", "raw", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    warnings, potcars = _write_inputs(config, config_text, structure, site, run_dir / "inputs")

    input_hashes = {name: sha256_file(run_dir / "inputs" / name) for name in INPUT_FILES}
    snapshot = {
        "config": {"source": display_path(config_path), "sha256": config_hash},
        "inputs": {"files": input_hashes, "input_hash": combined_hash(input_hashes)},
        "potcars": potcars,
        "structure": structure_info,
        "git": git_state(),
        "environment": environment_state(),
    }

    if existing:
        action = "regenerated"
        append_event(run_dir, "inputs_regenerated", "ok", "Inputs re-rendered from config.", updates=snapshot)
    else:
        action = "created"
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "run_id": config.run_id,
            "stage": config.run.stage,
            "system": config.run.system,
            "calc_type": config.run.calc_type,
            "campaign": config.run.campaign,
            "objective": config.run.objective,
            "sweep": config.run.sweep.model_dump() if config.run.sweep else None,
            "created_utc": utc_now(),
            "vasp": {"version": None},
            "hpc": {
                "job_id": None,
                "nodes": config.hpc.nodes,
                "ntasks": config.hpc.ntasks,
                "walltime": config.hpc.walltime,
            },
            "events": [],
            **snapshot,
        }
        write_json(manifest_path, manifest)
        append_event(run_dir, "prepared", "ok", "Run directory and inputs created.")

    if warnings:
        append_event(run_dir, "prepare_warnings", "warn", "; ".join(warnings))

    write_json(
        run_dir / "metrics.json",
        {"run_id": config.run_id, "calc_type": config.run.calc_type, "status": "prepared", "problems": []},
    )
    write_run_report(run_dir)
    return PrepareResult(config.run_id, run_dir, action, warnings, potcar_written=bool(potcars))


def copy_inputs_to_raw(run_dir: Path) -> List[str]:
    """Copy the input deck into ``raw/`` (VASP's working directory); returns copied names."""

    copied = []
    for name in INPUT_FILES:
        src = run_dir / "inputs" / name
        if src.exists():
            shutil.copy2(src, run_dir / "raw" / name)
            copied.append(name)
    return copied


def load_config_for_run(run_dir: Path) -> Optional[RunConfig]:
    """The config snapshot stored in a run directory (None if absent/invalid)."""

    snapshot = run_dir / "inputs" / "config.yaml"
    if not snapshot.exists():
        return None
    try:
        return load_run_config(snapshot)
    except ValueError:
        return None
