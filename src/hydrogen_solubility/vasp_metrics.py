"""Parse VASP text outputs and build ``metrics.json`` payloads.

Convergence is judged from explicit evidence, never assumed:

* **completed** -- OUTCAR contains VASP's final timing section, i.e. VASP exited
  normally (not killed by walltime or a crash).
* **electronic** -- the last ionic step finished its SCF loop in fewer than NELM
  iterations (counted from OSZICAR), and OUTCAR does not report
  "EDIFF was not reached".
* **ionic** -- only required for relaxations (IBRION 1/2/3 with NSW > 0): OUTCAR
  must say "reached required accuracy".
* **vibrations** -- finite-difference runs (IBRION 5-8) must print the dynamical
  matrix eigenvalues.

The headline energy is ``energy(sigma->0)`` (``E0``), which removes most of the
smearing contribution; the free energy ``TOTEN`` is stored alongside it.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION_RE = re.compile(r"^\s*vasp\.(\S+)", re.MULTILINE)
NIONS_RE = re.compile(r"NIONS\s*=\s*(\d+)")
NELM_RE = re.compile(r"\bNELM\s*=\s*(\d+)")
NSW_RE = re.compile(r"\bNSW\s*=\s*(\d+)")
IBRION_RE = re.compile(r"\bIBRION\s*=\s*(-?\d+)")
ISIF_RE = re.compile(r"\bISIF\s*=\s*(\d+)")
TOTEN_RE = re.compile(r"free\s+energy\s+TOTEN\s*=\s*([-+0-9.Ee]+)")
SIGMA0_RE = re.compile(r"energy\(sigma->0\)\s*=\s*([-+0-9.Ee]+)")
PRESSURE_RE = re.compile(r"external pressure\s*=\s*([-+0-9.Ee]+)\s*kB")
ELAPSED_RE = re.compile(r"Elapsed time \(sec\):\s*([0-9.]+)")
SCF_ABORT_RE = re.compile(r"aborting loop([^\n]*)")
IONIC_REACHED_RE = re.compile(r"reached required accuracy", re.IGNORECASE)
COMPLETED_RE = re.compile(r"General timing and accounting")
FREQ_RE = re.compile(
    r"^\s*\d+\s+(f/i|f)\s*=\s*[0-9.]+\s+THz\s+[0-9.]+\s+2PiTHz\s+([0-9.]+)\s+cm-1\s+([0-9.]+)\s+meV",
    re.MULTILINE,
)

OSZ_SCF_RE = re.compile(r"^\s*(?:DAV|RMM|CG|SDA|DIA|ORT|EDD)\s*:\s*(\d+)", re.MULTILINE)
OSZ_IONIC_RE = re.compile(r"^\s*(\d+)\s+F=\s*([-+0-9.Ee]+)\s+E0=\s*([-+0-9.Ee]+)", re.MULTILINE)

RELAX_IBRIONS = {1, 2, 3}
FINITE_DIFF_IBRIONS = {5, 6, 7, 8}


@dataclass
class Frequency:
    """One normal mode from a finite-difference calculation."""

    meV: float
    cm1: float
    imaginary: bool


@dataclass
class OutcarData:
    vasp_version: Optional[str] = None
    nions: Optional[int] = None
    nelm: Optional[int] = None
    nsw: Optional[int] = None
    ibrion: Optional[int] = None
    isif: Optional[int] = None
    free_energy_eV: Optional[float] = None
    energy_sigma0_eV: Optional[float] = None
    pressure_kB: Optional[float] = None
    max_force_eV_A: Optional[float] = None
    elapsed_s: Optional[float] = None
    completed: bool = False
    ediff_not_reached: bool = False
    ionic_reached: bool = False
    frequencies: List[Frequency] = field(default_factory=list)


@dataclass
class OszicarData:
    ionic_steps: int = 0
    scf_steps_last: Optional[int] = None
    final_free_energy_eV: Optional[float] = None
    final_e0_eV: Optional[float] = None


def _last_float(pattern: re.Pattern, text: str) -> Optional[float]:
    matches = pattern.findall(text)
    return float(matches[-1]) if matches else None


def _first_int(pattern: re.Pattern, text: str) -> Optional[int]:
    match = pattern.search(text)
    return int(match.group(1)) if match else None


def _last_max_force(text: str, nions: Optional[int]) -> Optional[float]:
    """Largest atomic force in the final ``TOTAL-FORCE`` block."""

    start = text.rfind("TOTAL-FORCE (eV/Angst)")
    if start < 0 or not nions:
        return None
    lines = text[start:].splitlines()[2 : 2 + nions]  # skip header and dashed rule
    forces = []
    for line in lines:
        parts = line.split()
        if len(parts) < 6:
            return None
        fx, fy, fz = (float(x) for x in parts[3:6])
        forces.append((fx * fx + fy * fy + fz * fz) ** 0.5)
    return max(forces) if forces else None


def _last_scf_unconverged(text: str) -> bool:
    """VASP 6 ends each SCF loop with "aborting loop because EDIFF is reached" or
    "aborting loop EDIFF was not reached (unconverged)"; inspect the last one."""

    aborts = SCF_ABORT_RE.findall(text)
    return bool(aborts) and "not reached" in aborts[-1]


def _frequencies(text: str) -> List[Frequency]:
    """Normal modes from the first eigenvalue block (VASP prints a second, mass-scaled one)."""

    start = text.find("Eigenvectors and eigenvalues of the dynamical matrix")
    if start < 0:
        return []
    end = text.find("Eigenvectors after division by SQRT(mass)", start)
    block = text[start : end if end > 0 else len(text)]
    return [Frequency(meV=float(m), cm1=float(c), imaginary=(kind == "f/i")) for kind, c, m in FREQ_RE.findall(block)]


def parse_outcar(path: Path) -> Optional[OutcarData]:
    """Parse OUTCAR; ``None`` if the file does not exist."""

    if not path.is_file():
        return None
    text = path.read_text(errors="ignore")
    version = VERSION_RE.search(text)
    nions = _first_int(NIONS_RE, text)
    return OutcarData(
        vasp_version=version.group(1) if version else None,
        nions=nions,
        nelm=_first_int(NELM_RE, text),
        nsw=_first_int(NSW_RE, text),
        ibrion=_first_int(IBRION_RE, text),
        isif=_first_int(ISIF_RE, text),
        free_energy_eV=_last_float(TOTEN_RE, text),
        energy_sigma0_eV=_last_float(SIGMA0_RE, text),
        pressure_kB=_last_float(PRESSURE_RE, text),
        max_force_eV_A=_last_max_force(text, nions),
        elapsed_s=_last_float(ELAPSED_RE, text),
        completed=bool(COMPLETED_RE.search(text)),
        ediff_not_reached=_last_scf_unconverged(text),
        ionic_reached=bool(IONIC_REACHED_RE.search(text)),
        frequencies=_frequencies(text),
    )


def parse_oszicar(path: Path) -> Optional[OszicarData]:
    """Parse OSZICAR; ``None`` if the file does not exist."""

    if not path.is_file():
        return None
    text = path.read_text(errors="ignore")
    ionic = OSZ_IONIC_RE.findall(text)
    data = OszicarData(ionic_steps=len(ionic))
    if ionic:
        data.final_free_energy_eV = float(ionic[-1][1])
        data.final_e0_eV = float(ionic[-1][2])
    # SCF iterations of the last completed ionic step lie between the last two "F=" lines.
    marks = list(OSZ_IONIC_RE.finditer(text))
    begin = marks[-2].end() if len(marks) >= 2 else 0
    end = marks[-1].start() if marks else len(text)
    scf = OSZ_SCF_RE.findall(text[begin:end])
    data.scf_steps_last = int(scf[-1]) if scf else None
    return data


# ---------------------------------------------------------------------------- metrics


def assess(outcar: Optional[OutcarData], oszicar: Optional[OszicarData]) -> Dict[str, Any]:
    """Turn parsed outputs into explicit checks and an overall status.

    Status values: ``not_started`` (no OUTCAR), ``incomplete`` (VASP did not exit
    normally: still running, crashed or hit walltime), ``unconverged`` (finished
    but a required check failed) and ``converged``.
    """

    if outcar is None:
        return {"status": "not_started", "checks": {}, "problems": ["raw/OUTCAR not found"]}

    problems: List[str] = []
    ibrion = outcar.ibrion if outcar.ibrion is not None else -1
    nsw = outcar.nsw or 0
    is_relax = ibrion in RELAX_IBRIONS and nsw > 0
    is_vib = ibrion in FINITE_DIFF_IBRIONS

    electronic: Optional[bool] = None
    if oszicar is not None and oszicar.scf_steps_last is not None and outcar.nelm:
        electronic = oszicar.scf_steps_last < outcar.nelm and not outcar.ediff_not_reached
    elif outcar.ediff_not_reached:
        electronic = False

    checks: Dict[str, Optional[bool]] = {
        "completed_normally": outcar.completed,
        "electronic_converged": electronic,
        "ionic_converged": outcar.ionic_reached if is_relax else None,
        "vibrations_parsed": bool(outcar.frequencies) if is_vib else None,
    }

    if not outcar.completed:
        problems.append("VASP did not finish normally (running, crashed, or out of walltime)")
    if electronic is False:
        problems.append("SCF did not converge within NELM in the last ionic step")
    if electronic is None:
        problems.append("could not determine SCF convergence (OSZICAR missing or unreadable)")
    if is_relax and not outcar.ionic_reached:
        problems.append("relaxation did not reach EDIFFG within NSW steps")
    if is_vib and not outcar.frequencies:
        problems.append("no vibrational frequencies found in OUTCAR")
    if outcar.energy_sigma0_eV is None and not is_vib:
        problems.append("no total energy found in OUTCAR")

    if not outcar.completed:
        status = "incomplete"
    elif problems:
        status = "unconverged"
    else:
        status = "converged"
    return {"status": status, "checks": checks, "problems": problems}


def build_metrics_payload(
    *,
    run_id: str,
    calc_type: str,
    outcar_path: Path,
    oszicar_path: Path,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct the ``metrics.json`` payload for one run (schema: docs/data_model.md)."""

    outcar = parse_outcar(outcar_path)
    oszicar = parse_oszicar(oszicar_path)
    verdict = assess(outcar, oszicar)

    energetics: Dict[str, Optional[float]] = {
        "energy_sigma0_eV": None,
        "free_energy_eV": None,
        "energy_per_atom_eV": None,
    }
    calculation: Dict[str, Any] = {}
    vibrations: Optional[Dict[str, Any]] = None
    if outcar is not None:
        e0 = outcar.energy_sigma0_eV
        energetics["energy_sigma0_eV"] = e0
        energetics["free_energy_eV"] = outcar.free_energy_eV
        if e0 is not None and outcar.nions:
            energetics["energy_per_atom_eV"] = e0 / outcar.nions
        calculation = {
            "vasp_version": outcar.vasp_version,
            "nions": outcar.nions,
            "ionic_steps": oszicar.ionic_steps if oszicar else None,
            "scf_steps_last_ionic": oszicar.scf_steps_last if oszicar else None,
            "nelm": outcar.nelm,
            "max_force_eV_A": outcar.max_force_eV_A,
            "pressure_kB": outcar.pressure_kB,
            "elapsed_s": outcar.elapsed_s,
        }
        if outcar.frequencies:
            vibrations = {
                "n_modes": len(outcar.frequencies),
                "n_imaginary": sum(1 for f in outcar.frequencies if f.imaginary),
                "modes": [asdict(f) for f in outcar.frequencies],
            }

    payload: Dict[str, Any] = {
        "run_id": run_id,
        "calc_type": calc_type,
        "status": verdict["status"],
        "problems": verdict["problems"],
        "checks": verdict["checks"],
        "energetics": energetics,
        "calculation": calculation,
        "artifacts": {"outcar": "raw/OUTCAR", "oszicar": "raw/OSZICAR", "contcar": "raw/CONTCAR"},
    }
    if vibrations is not None:
        payload["vibrations"] = vibrations
    if extra:
        payload.update(extra)
    return payload
