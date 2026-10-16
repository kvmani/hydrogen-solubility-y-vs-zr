import pytest
from conftest import oszicar_text, outcar_text

from hydrogen_solubility.vasp_metrics import build_metrics_payload, parse_oszicar, parse_outcar


def _payload(tmp_path, scf_counts=(12,), **kw):
    (tmp_path / "OUTCAR").write_text(outcar_text(**kw))
    (tmp_path / "OSZICAR").write_text(oszicar_text(list(scf_counts), [kw["e0"]] * len(scf_counts)))
    return build_metrics_payload(
        run_id="X", calc_type="t", outcar_path=tmp_path / "OUTCAR", oszicar_path=tmp_path / "OSZICAR"
    )


def test_static_run_converged(tmp_path):
    m = _payload(tmp_path, nions=2, e0=-12.5)
    assert m["status"] == "converged" and m["problems"] == []
    assert m["energetics"]["energy_sigma0_eV"] == pytest.approx(-12.5)
    assert m["energetics"]["energy_per_atom_eV"] == pytest.approx(-6.25)
    assert m["checks"]["ionic_converged"] is None  # not applicable to a single point
    assert m["calculation"]["vasp_version"] == "6.4.2"
    assert m["calculation"]["max_force_eV_A"] == pytest.approx((0.001**2 + 0.002**2) ** 0.5)


def test_scf_hitting_nelm_is_unconverged_even_with_an_energy(tmp_path):
    m = _payload(tmp_path, nions=2, e0=-12.5, nelm=40, scf_counts=(40,))
    assert m["status"] == "unconverged"
    assert m["checks"]["electronic_converged"] is False


def test_vasp6_unconverged_marker(tmp_path):
    m = _payload(tmp_path, nions=2, e0=-12.5, scf_converged=False)
    assert m["checks"]["electronic_converged"] is False


def test_only_last_ionic_step_scf_matters(tmp_path):
    # First ionic step needed all 60 iterations, the final one converged: run is fine.
    m = _payload(tmp_path, nions=2, e0=-1.0, nsw=10, ibrion=2, ionic_reached=True, scf_counts=(60, 8))
    assert m["checks"]["electronic_converged"] is True and m["status"] == "converged"
    assert parse_oszicar(tmp_path / "OSZICAR").ionic_steps == 2


def test_relaxation_must_reach_ediffg(tmp_path):
    m = _payload(tmp_path, nions=37, e0=-300.0, nsw=100, ibrion=2, ionic_reached=False)
    assert m["status"] == "unconverged"
    assert any("EDIFFG" in p for p in m["problems"])


def test_killed_job_is_incomplete(tmp_path):
    m = _payload(tmp_path, nions=2, e0=-12.5, completed=False)
    assert m["status"] == "incomplete"


def test_missing_outcar_is_not_started(tmp_path):
    m = build_metrics_payload(run_id="X", calc_type="t", outcar_path=tmp_path / "no", oszicar_path=tmp_path / "no")
    assert m["status"] == "not_started"


def test_vibrational_frequencies_are_parsed_once(tmp_path):
    m = _payload(
        tmp_path,
        nions=37,
        e0=-300.0,
        nsw=1,
        ibrion=5,
        frequencies_meV=(150.0, 140.0, 12.0),
        imaginary=(False, False, True),
    )
    assert m["status"] == "converged"
    vib = m["vibrations"]
    assert vib["n_modes"] == 3 and vib["n_imaginary"] == 1
    assert [round(x["meV"], 3) for x in vib["modes"]] == [150.0, 140.0, 12.0]


def test_outcar_parser_tolerates_garbage(tmp_path):
    (tmp_path / "OUTCAR").write_text("not a vasp file\n")
    data = parse_outcar(tmp_path / "OUTCAR")
    assert data.energy_sigma0_eV is None and not data.completed
