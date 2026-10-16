"""End-to-end: plan -> prepare -> dryrun/smoke/submit -> collect -> analyze, with fake
Slurm/VASP executables and synthetic VASP outputs whose correct analysis is known."""

import math

import pytest
from conftest import write_outputs

from hydrogen_solubility import structures as st
from hydrogen_solubility import thermo
from hydrogen_solubility.cli import main
from hydrogen_solubility.planner import write_plan
from hydrogen_solubility.provenance import read_json


def _plan(campaigns, name, tmp_path):
    out, planned, _ = write_plan(campaigns / f"{name}.yaml", tmp_path / "generated" / name)
    return out, {p.config.run_id: p.config for p in planned}


# ------------------------------------------------------------------ Stage 1a + pipeline


def _e_atom(system, encut, spacing):
    """Synthetic energy surface: ENCUT converges at 600 (Y) / 550 (Zr) eV, k at 0.20 / 0.13 1/A."""

    scale = {"Y": 50.0, "Zr": 40.0}[system]
    k_coeff = {"Y": 0.5, "Zr": 2.0}[system]
    return -6.0 - 0.2 * math.exp(-(encut - 300.0) / scale) + k_coeff * spacing**4


def test_stage1_pipeline_and_convergence_analysis(workspace, fake_cluster, campaigns, tmp_path, capsys):
    gen, configs = _plan(campaigns, "stage1_convergence", tmp_path)
    assert main(["prepare", str(gen)]) == 0

    # Regression for the original bug: every run's INCAR must carry its own ENCUT.
    for run_id, cfg in configs.items():
        incar = (workspace["runs"] / run_id / "inputs" / "INCAR").read_text()
        assert f"ENCUT  = {cfg.vasp.incar['ENCUT']}" in incar
    y_ref = workspace["runs"] / "Y_stage1_ref"
    assert "19 19 10" in (y_ref / "inputs" / "KPOINTS").read_text()  # spacing 0.11 on alpha-Y
    manifest = read_json(y_ref / "manifest.json")
    assert [p["label"] for p in manifest["potcars"]] == ["Y_sv"] and manifest["git"]["commit"]
    assert "PAW_PBE Y_sv" in (y_ref / "inputs" / "POTCAR").read_text()

    one = str(gen / "Y_stage1_ref.yaml")
    assert main(["run", "--mode", "submit", one]) == 1  # refused: no smoke test yet
    assert main(["run", "--mode", "dryrun", str(gen)]) == 0
    assert main(["run", "--mode", "smoke", str(gen)]) == 0
    assert "SMOKE OK" in next(y_ref.glob("logs/*_smoke/smoke_local.log")).read_text()
    assert not (y_ref / "raw" / "INCAR").exists()  # smoke works on a scratch copy
    assert main(["run", "--mode", "submit", one]) == 0
    manifest = read_json(y_ref / "manifest.json")
    assert manifest["hpc"]["job_id"] == "4242" and manifest["hpc"]["partition"] == "debug"
    assert read_json(y_ref / "metrics.json")["status"] == "submitted"
    assert main(["run", "--mode", "submit", one]) == 1  # refused: already submitted
    job = next(y_ref.glob("logs/*_submit/job.sbatch")).read_text()
    assert "#SBATCH --account=proj123" in job and "collect --quiet" in job

    for run_id, cfg in configs.items():
        spacing = cfg.vasp.kpoints.spacing
        write_outputs(
            workspace["runs"] / run_id, nions=2, e0=2 * _e_atom(cfg.run.system, cfg.vasp.incar["ENCUT"], spacing)
        )
    capsys.readouterr()
    assert main(["collect"]) == 0
    assert read_json(y_ref / "metrics.json")["status"] == "converged"
    assert "Y_stage1_ref" in (workspace["results"] / "INDEX.md").read_text()

    assert main(["analyze", "convergence"]) == 0
    summary = (workspace["results"] / "analysis" / "convergence" / "summary.md").read_text()
    assert "ENCUT: 600" in summary and "spacing: 0.13" in summary


def test_prepare_refuses_to_orphan_existing_results(workspace, campaigns, tmp_path):
    gen, _ = _plan(campaigns, "stage1_relax", tmp_path)
    assert main(["prepare", str(gen)]) == 0
    write_outputs(workspace["runs"] / "Y_stage1_relax", nions=2, e0=-12.0, nsw=60, ibrion=2, ionic_reached=True)
    path = gen / "Y_stage1_relax.yaml"
    path.write_text(path.read_text().replace("EDIFF: 1.0e-07", "EDIFF: 1.0e-06"))
    assert main(["prepare", str(path)]) == 1  # physics changed but outputs exist -> must use a new run_id
    path.write_text(path.read_text().replace("01:00:00", "02:00:00"))
    path.write_text(path.read_text().replace("EDIFF: 1.0e-06", "EDIFF: 1.0e-07"))
    assert main(["prepare", str(path)]) == 0  # only the walltime changed: fine


# ---------------------------------------------------------------- Stages 1b-4 + model

E_H2 = -6.77
E_ATOM = {"Y": -6.40, "Zr": -8.55}
DE_SITE = {
    ("Y", "tetrahedral"): -0.20,
    ("Y", "octahedral"): -0.10,
    ("Zr", "tetrahedral"): -0.40,
    ("Zr", "octahedral"): -0.30,
}
DE_HYD = {"Y": -1.00, "Zr": -0.85}
MODES = {"tetrahedral": [120.0, 120.0, 140.0], "octahedral": [80.0, 80.0, 100.0]}
H2_MODES = [540.0, 5.0, 4.0, 3.0, 2.0, 1.0]
HYD_MODES = [130.0] * 24


def _finish(workspace, run_id, e0, nions, **kw):
    run_dir = workspace["runs"] / run_id
    write_outputs(run_dir, nions=nions, e0=e0, contcar=(run_dir / "inputs" / "POSCAR").read_text(), **kw)
    assert main(["collect", run_id]) == 0


def test_full_chain_to_solubility(workspace, campaigns, tmp_path):
    relaxed = {"Y": (3.66, 5.68), "Zr": (3.23, 5.17)}
    gen, _ = _plan(campaigns, "stage1_relax", tmp_path)
    assert main(["prepare", str(gen)]) == 0
    for system, (a, c) in relaxed.items():
        run_dir = workspace["runs"] / f"{system}_stage1_relax"
        write_outputs(
            run_dir,
            nions=2,
            e0=2 * E_ATOM[system],
            nsw=60,
            ibrion=2,
            ionic_reached=True,
            contcar=st.hcp_primitive(system, a, c).to_poscar(),
        )
    assert main(["collect"]) == 0

    gen, _ = _plan(campaigns, "stage2_h_energetics", tmp_path)
    assert main(["prepare", str(gen)]) == 0
    poscar = st.Structure.read(workspace["runs"] / "Zr_stage2_hO" / "inputs" / "POSCAR")
    assert st.classify_h_site(poscar) == "octahedral"
    assert poscar.lengths()[0] == pytest.approx(3 * 3.23) and poscar.lengths()[2] == pytest.approx(2 * 5.17)
    relax = dict(nsw=100, ibrion=2, ionic_reached=True)
    for system in ("Y", "Zr"):
        host = 36 * E_ATOM[system]
        _finish(workspace, f"{system}_stage2_host", host, 36)
        for label, site in (("hT", "tetrahedral"), ("hO", "octahedral")):
            _finish(workspace, f"{system}_stage2_{label}", host + 0.5 * E_H2 + DE_SITE[(system, site)], 37, **relax)
    _finish(workspace, "H2_stage2_molecule", E_H2, 2, nsw=50, ibrion=2, ionic_reached=True)

    gen, _ = _plan(campaigns, "stage3_vibrations", tmp_path)
    assert main(["prepare", str(gen)]) == 0
    selective = st.Structure.read(workspace["runs"] / "Y_stage3_vib_hT" / "inputs" / "POSCAR").selective
    assert sum(f[0] for f in selective) == 1  # only the H atom moves
    vib = dict(nsw=1, ibrion=5)
    for system in ("Y", "Zr"):
        for label, site in (("hT", "tetrahedral"), ("hO", "octahedral")):
            _finish(workspace, f"{system}_stage3_vib_{label}", -1.0, 37, frequencies_meV=MODES[site], **vib)
    _finish(
        workspace,
        "H2_stage3_vib_molecule",
        -1.0,
        2,
        frequencies_meV=H2_MODES,
        imaginary=[False, True, True, False, False, False],
        **vib,
    )
    assert read_json(workspace["runs"] / "H2_stage3_vib_molecule" / "metrics.json")["warnings"] == []

    gen, _ = _plan(campaigns, "stage4_hydrides", tmp_path)
    assert main(["prepare", str(gen)]) == 0
    for system in ("Y", "Zr"):
        e_cell = 4 * E_ATOM[system] + 8 * (0.5 * E_H2 + DE_HYD[system])
        _finish(workspace, f"{system}_stage4_hydride", e_cell, 12, nsw=60, ibrion=2, ionic_reached=True)
    gen, _ = _plan(campaigns, "stage4_hydride_vibrations", tmp_path)
    assert main(["prepare", str(gen)]) == 0
    for system in ("Y", "Zr"):
        _finish(workspace, f"{system}_stage4_vib_hydride", -1.0, 12, frequencies_meV=HYD_MODES, **vib)

    assert main(["analyze", "solubility"]) == 0
    out = workspace["results"] / "analysis" / "solubility"
    summary = (out / "summary.md").read_text()
    assert "Missing inputs" not in summary

    # Independent hand calculation of the 600 K TSS from the same formulas.
    t = 600.0
    f_h2 = thermo.harmonic_free_energy([540.0], t)
    expected = {}
    for system in ("Y", "Zr"):
        g_hyd = DE_HYD[system] + thermo.harmonic_free_energy(HYD_MODES, t) / 8 - 0.5 * f_h2
        x = 0.0
        for site, n in (("tetrahedral", 2), ("octahedral", 1)):
            g = DE_SITE[(system, site)] + thermo.harmonic_free_energy(MODES[site], t) - 0.5 * f_h2
            x += n / (1.0 + math.exp((g - g_hyd) / (thermo.K_B * t)))
        expected[system] = x
    assert f"Y {expected['Y']:.3g}, Zr {expected['Zr']:.3g}" in summary
    assert (out / "solubility_vs_T.csv").exists() and (out / "site_energetics.csv").exists()


def test_unstable_site_is_excluded(workspace, campaigns, tmp_path):
    """An O-site H that relaxes into a T site must not be counted as an O site."""

    gen, _ = _plan(campaigns, "stage1_relax", tmp_path)
    assert main(["prepare", str(gen)]) == 0
    write_outputs(
        workspace["runs"] / "Y_stage1_relax",
        nions=2,
        e0=-12.8,
        nsw=60,
        ibrion=2,
        ionic_reached=True,
        contcar=st.hcp_primitive("Y", 3.66, 5.68).to_poscar(),
    )
    assert main(["collect", "Y_stage1_relax"]) == 0
    gen, _ = _plan(campaigns, "stage2_h_energetics", tmp_path)
    assert main(["prepare", str(gen / "Y_stage2_hO.yaml")]) == 0
    t_site = st.hcp_supercell("Y", 3.66, 5.68, (3, 3, 2), "tetrahedral").to_poscar()
    write_outputs(
        workspace["runs"] / "Y_stage2_hO", nions=37, e0=-237.0, nsw=100, ibrion=2, ionic_reached=True, contcar=t_site
    )
    assert main(["collect", "Y_stage2_hO"]) == 0
    metrics = read_json(workspace["runs"] / "Y_stage2_hO" / "metrics.json")
    assert metrics["structure_check"]["final_site"] == "tetrahedral"
    assert any("not a local minimum" in w for w in metrics["warnings"])


def test_walltime_rerun_with_resubmit(workspace, fake_cluster, campaigns, tmp_path):
    """The documented recipe for a job that ran out of walltime."""

    gen, _ = _plan(campaigns, "stage1_relax", tmp_path)
    cfg = str(gen / "Y_stage1_relax.yaml")
    run_dir = workspace["runs"] / "Y_stage1_relax"
    assert main(["prepare", cfg]) == 0
    assert main(["run", "--mode", "smoke", cfg]) == 0
    assert main(["run", "--mode", "submit", cfg]) == 0
    write_outputs(run_dir, nions=2, e0=-12.8, nsw=60, ibrion=2, completed=False)
    assert main(["collect", "Y_stage1_relax"]) == 0
    assert read_json(run_dir / "metrics.json")["status"] == "incomplete"

    path = gen / "Y_stage1_relax.yaml"
    path.write_text(path.read_text().replace("01:00:00", "04:00:00"))
    assert main(["prepare", cfg]) == 0  # resources only: same run id, smoke test still valid
    assert main(["run", "--mode", "submit", cfg]) == 1  # outputs exist: refused without --resubmit
    assert main(["run", "--mode", "submit", "--resubmit", cfg]) == 0
    assert list((run_dir / "attempts").iterdir())[0].joinpath("OUTCAR").exists()
    assert not (run_dir / "raw" / "OUTCAR").exists()
    job = max(run_dir.glob("logs/*_submit*/job.sbatch"), key=lambda p: p.stat().st_mtime_ns).read_text()
    assert "#SBATCH --time=04:00:00" in job
