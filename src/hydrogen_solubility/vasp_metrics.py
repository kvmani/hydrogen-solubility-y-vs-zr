"""Parse VASP outputs and build metrics payloads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


TOTEN_RE = re.compile(r"free\s+energy\s+TOTEN\s*=\s*([\-0-9.Ee+]+)\s+eV")
NIONS_RE = re.compile(r"NIONS\s*=\s*([0-9]+)")
EDIFF_REACHED_RE = re.compile(r"aborting loop because EDIFF is reached", re.IGNORECASE)
EDIFF_NOT_REACHED_RE = re.compile(r"EDIFF.*not reached", re.IGNORECASE)
IONIC_CONVERGED_RE = re.compile(
    r"reached required accuracy\s*-\s*stopping structural energy minimisation", re.IGNORECASE
)
NSW_RE = re.compile(r"NSW\s*=\s*([0-9]+)")

OSZICAR_F_RE = re.compile(r"F=\s*([\-0-9.Ee+]+)")
OSZICAR_E0_RE = re.compile(r"E0=\s*([\-0-9.Ee+]+)")


@dataclass
class OutcarSummary:
    """Minimal values parsed from OUTCAR."""

    total_energy_eV: float | None
    nions: int | None
    electronic_converged: bool | None
    ionic_converged: bool | None
    nsw: int | None


@dataclass
class OszicarSummary:
    """Minimal values parsed from OSZICAR."""

    final_free_energy_eV: float | None
    final_e0_energy_eV: float | None


def parse_outcar(path: Path) -> OutcarSummary:
    """Extract core convergence and energy information from OUTCAR."""

    if not path.exists():
        return OutcarSummary(
            total_energy_eV=None,
            nions=None,
            electronic_converged=None,
            ionic_converged=None,
            nsw=None,
        )

    text = path.read_text(errors="ignore")

    toten_matches = TOTEN_RE.findall(text)
    total_energy = float(toten_matches[-1]) if toten_matches else None

    nions_match = NIONS_RE.search(text)
    nions = int(nions_match.group(1)) if nions_match else None

    nsw_match = NSW_RE.search(text)
    nsw = int(nsw_match.group(1)) if nsw_match else None

    if EDIFF_NOT_REACHED_RE.search(text):
        electronic = False
    elif EDIFF_REACHED_RE.search(text) or total_energy is not None:
        electronic = True
    else:
        electronic = None

    if IONIC_CONVERGED_RE.search(text):
        ionic = True
    elif nsw == 0:
        # Static run: no ionic optimization expected.
        ionic = True
    else:
        ionic = None

    return OutcarSummary(
        total_energy_eV=total_energy,
        nions=nions,
        electronic_converged=electronic,
        ionic_converged=ionic,
        nsw=nsw,
    )


def parse_oszicar(path: Path) -> OszicarSummary:
    """Extract final energies from OSZICAR as fallback/context."""

    if not path.exists():
        return OszicarSummary(final_free_energy_eV=None, final_e0_energy_eV=None)

    text = path.read_text(errors="ignore")

    f_matches = OSZICAR_F_RE.findall(text)
    e0_matches = OSZICAR_E0_RE.findall(text)

    f_val = float(f_matches[-1]) if f_matches else None
    e0_val = float(e0_matches[-1]) if e0_matches else None

    return OszicarSummary(final_free_energy_eV=f_val, final_e0_energy_eV=e0_val)


def build_stage1_metrics_payload(
    *,
    run_id: str,
    outcar_path: Path,
    oszicar_path: Path,
) -> dict[str, Any]:
    """Construct a `metrics.json` payload from VASP outputs."""

    outcar = parse_outcar(outcar_path)
    oszicar = parse_oszicar(oszicar_path)

    total_energy = outcar.total_energy_eV
    if total_energy is None:
        total_energy = oszicar.final_free_energy_eV

    energy_per_atom = None
    if total_energy is not None and outcar.nions and outcar.nions > 0:
        energy_per_atom = total_energy / outcar.nions

    electronic_ok = outcar.electronic_converged
    ionic_ok = outcar.ionic_converged

    if electronic_ok is True and (ionic_ok is True or ionic_ok is None):
        status = "success"
    elif total_energy is not None:
        status = "partial"
    else:
        status = "failed"

    return {
        "run_id": run_id,
        "status": status,
        "energetics": {
            "total_energy_eV": total_energy,
            "energy_per_atom_eV": energy_per_atom,
            "formation_energy_eV": None,
            "h_solution_energy_eV": None,
            "oszicar_final_e0_eV": oszicar.final_e0_energy_eV,
        },
        "checks": {
            "electronic_converged": electronic_ok,
            "ionic_converged": ionic_ok,
            "encut_converged": None,
            "kmesh_converged": None,
        },
        "artifacts": {
            "outcar": str(outcar_path),
            "oszicar": str(oszicar_path),
            "summary_table": "parsed/summary.csv",
        },
        "notes": "Parsed from VASP outputs by tools/extract_metrics.py",
    }

