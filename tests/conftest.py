"""Shared fixtures: an isolated workspace, fake POTCARs, fake Slurm/VASP tools and
synthetic VASP outputs written in the real OUTCAR/OSZICAR formats."""

from __future__ import annotations

import os
import shutil
import stat
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pytest
import yaml

from hydrogen_solubility.config_models import load_site_config
from hydrogen_solubility.paths import REPO_ROOT

CAMPAIGNS = REPO_ROOT / "configs" / "campaigns"


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Path]:
    """Isolated results dir, site config and POTCAR library; nothing touches the repo."""

    results = tmp_path / "results"
    potcars = tmp_path / "potpaw_PBE"
    for label, element, enmax in (("Y_sv", "Y", 202.256), ("Zr_sv", "Zr", 229.898), ("H", "H", 250.000)):
        (potcars / label).mkdir(parents=True)
        (potcars / label / "POTCAR").write_text(
            f"  PAW_PBE {label} 06Sep2000\n   TITEL  = PAW_PBE {label} 06Sep2000\n"
            f"   ENMAX  =  {enmax}; ENMIN  =  150.000 eV\n fake dataset for {element}\n End of Dataset\n"
        )
    site = tmp_path / "site.yaml"
    site.write_text(
        yaml.safe_dump(
            {
                "slurm": {"partition": "debug", "account": "proj123"},
                "environment": {"module_purge": False, "modules": []},
                "vasp": {"launch_command": "srun", "potcar_root": str(potcars)},
                "paths": {"results_root": str(results / "runs")},
            }
        )
    )
    monkeypatch.setenv("HSOL_SITE", str(site))
    monkeypatch.setenv("HSOL_RESULTS_DIR", str(results))
    return {"root": tmp_path, "results": results, "runs": results / "runs", "site": site, "potcars": potcars}


@pytest.fixture()
def site(workspace):
    return load_site_config()


@pytest.fixture()
def fake_cluster(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Executables named vasp_std, srun and sbatch on PATH (sbatch prints job id 4242)."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    scripts = {
        "vasp_std": "#!/bin/sh\nexit 0\n",
        "srun": '#!/bin/sh\nexec "$@"\n',
        "sbatch": textwrap.dedent(
            """\
            #!/bin/sh
            case "$1" in
              --test-only) echo "sbatch: Job 4242 to start at now"; exit 0 ;;
              --parsable) echo "4242"; exit 0 ;;
            esac
            exit 1
            """
        ),
    }
    for name, body in scripts.items():
        path = bin_dir / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return bin_dir


@pytest.fixture()
def campaigns(tmp_path: Path) -> Path:
    """Copy of configs/campaigns with the converged settings filled in."""

    target = tmp_path / "campaigns"
    shutil.copytree(CAMPAIGNS, target)
    (target / "converged_settings.yaml").write_text(
        yaml.safe_dump({"defaults": {"vasp": {"incar": {"ENCUT": 520}, "kpoints": {"spacing": 0.15}}}})
    )
    return target


# ---------------------------------------------------------------- synthetic VASP outputs


def outcar_text(
    *,
    nions: int,
    e0: float,
    free: Optional[float] = None,
    nelm: int = 60,
    nsw: int = 0,
    ibrion: int = -1,
    completed: bool = True,
    ionic_reached: bool = False,
    scf_converged: bool = True,
    frequencies_meV: Sequence[float] = (),
    imaginary: Sequence[bool] = (),
    version: str = "6.4.2",
) -> str:
    free = e0 - 0.001 if free is None else free
    abort = (
        "aborting loop because EDIFF is reached"
        if scf_converged
        else "aborting loop EDIFF was not reached (unconverged)"
    )
    lines = [
        f" vasp.{version} 20Jul23 (build Aug 01 2023 12:00:00) complex",
        f"   number of dos      NEDOS =    301   number of ions     NIONS = {nions:6d}",
        f"   NELM   = {nelm:6d};   NELMIN=  2; NELMDL= -5     # of ELM steps",
        f"   NSW    = {nsw:6d}    number of steps for IOM",
        f"   IBRION = {ibrion:6d}    ionic relax: 0-MD 1-quasi-New 2-CG",
        "   ISIF   =      2    stress and relaxation",
        f"------------------------ {abort} ------------------------",
        " POSITION                                       TOTAL-FORCE (eV/Angst)",
        " -----------------------------------------------------------------------------------",
    ]
    lines += ["      0.00000      0.00000      0.00000         0.001000      0.000000      0.002000"] * nions
    lines += [
        " -----------------------------------------------------------------------------------",
        "  FREE ENERGIE OF THE ION-ELECTRON SYSTEM (eV)",
        f"  free  energy   TOTEN  = {free:20.8f} eV",
        f"  energy  without entropy= {e0:20.8f}  energy(sigma->0) = {e0:20.8f}",
        "  external pressure =        0.12 kB  Pullay stress =        0.00 kB",
    ]
    if ionic_reached:
        lines.append(" reached required accuracy - stopping structural energy minimisation")
    if frequencies_meV:
        lines += [
            " Eigenvectors and eigenvalues of the dynamical matrix",
            " ----------------------------------------------------",
        ]
        flags = list(imaginary) or [False] * len(frequencies_meV)
        for i, (mev, im) in enumerate(zip(frequencies_meV, flags), start=1):
            cm1 = mev * 8.0655439
            thz = cm1 / 33.35641
            kind = "f/i=" if im else "f  ="
            lines.append(
                f"   {i} {kind} {thz:12.6f} THz {thz * 6.2831853:12.6f} 2PiTHz {cm1:12.6f} cm-1 {mev:12.6f} meV"
            )
        lines.append(" Eigenvectors after division by SQRT(mass)")
    if completed:
        lines += [" General timing and accounting informations for this job:", "  Elapsed time (sec):      123.456"]
    return "\n".join(lines) + "\n"


def oszicar_text(scf_counts: List[int], energies: List[float]) -> str:
    out = ["       N       E                     dE             d eps       ncg     rms          rms(c)"]
    for step, (count, energy) in enumerate(zip(scf_counts, energies), start=1):
        out += [f"DAV: {i:3d}    0.1E+01    0.1E+01   -0.1E+01   100   0.1E+01" for i in range(1, count + 1)]
        out.append(f"   {step} F= {energy - 0.001:.8E} E0= {energy:.8E}  d E =-.1E+00")
    return "\n".join(out) + "\n"


def write_outputs(
    run_dir: Path, *, contcar: Optional[str] = None, scf_counts: Optional[List[int]] = None, **kw
) -> None:
    """Drop synthetic OUTCAR/OSZICAR (and optional CONTCAR) into ``run_dir/raw``."""

    raw = run_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "OUTCAR").write_text(outcar_text(**kw))
    counts = scf_counts or [12]
    (raw / "OSZICAR").write_text(oszicar_text(counts, [kw["e0"]] * len(counts)))
    if contcar is not None:
        (raw / "CONTCAR").write_text(contcar)
