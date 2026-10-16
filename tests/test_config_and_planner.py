import copy

import pytest
import yaml

from hydrogen_solubility.config_models import ConfigValidationError, parse_run_config
from hydrogen_solubility.planner import PlanError, deep_merge, expand_campaign, load_campaign, write_plan

BASE = {
    "schema_version": "2.0",
    "run": {
        "run_id": "Y_stage1_ref",
        "stage": "stage1",
        "system": "Y",
        "calc_type": "host_convergence",
        "objective": "Convergence reference point for alpha-Y.",
    },
    "structure": {"builder": "hcp_primitive", "a_A": 3.647, "c_A": 5.731, "source": "test"},
    "vasp": {
        "incar": {"ENCUT": 500, "PREC": "Accurate", "EDIFF": 1e-7, "ISMEAR": 1, "SIGMA": 0.2, "IBRION": -1, "NSW": 0},
        "kpoints": {"grid": [16, 16, 10]},
    },
    "potcars": {"Y": "Y_sv"},
    "hpc": {"ntasks": 8, "walltime": "00:30:00"},
}


def _with(path, value):
    payload = copy.deepcopy(BASE)
    node = payload
    keys = path.split(".")
    for k in keys[:-1]:
        node = node[k]
    if value is None:
        node.pop(keys[-1])
    else:
        node[keys[-1]] = value
    return payload


def test_valid_config_parses():
    cfg = parse_run_config(copy.deepcopy(BASE))
    assert cfg.run_id == "Y_stage1_ref" and cfg.dependencies() == []


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        ("run.run_id", "Zr_stage1_ref", "must start with 'Y_stage1_'"),
        ("vasp.incar.NSW", None, "missing required tags"),
        ("vasp.incar.encut", 400, "upper-case"),
        ("structure.builder", "fluorite_dihydride", "expects structure.builder"),
        ("structure.h_site", "tetrahedral", "only meaningful"),
        ("potcars", {"Zr": "Zr_sv"}, "element 'Y'"),
        ("vasp.kpoints", {"grid": [4, 4, 4], "spacing": 0.2}, "exactly one"),
        ("hpc.walltime", "8 hours", "HH:MM:SS"),
        ("structure.kpoint_grid", [1, 1, 1], "Extra inputs"),
    ],
)
def test_invalid_configs_are_rejected_with_a_useful_message(path, value, message):
    with pytest.raises(ConfigValidationError, match=message):
        parse_run_config(_with(path, value))


def test_unquoted_yaml_walltime_is_accepted():
    payload = yaml.safe_load(yaml.safe_dump(BASE).replace("00:30:00", "12:00:00").replace("'12:00:00'", "12:00:00"))
    assert isinstance(payload["hpc"]["walltime"], int)  # what PyYAML does with an unquoted value
    assert parse_run_config(payload).hpc.walltime == "12:00:00"


def test_science_hash_ignores_resources_only():
    a = parse_run_config(copy.deepcopy(BASE))
    b = parse_run_config(_with("hpc.walltime", "04:00:00"))
    c = parse_run_config(_with("vasp.incar.ENCUT", 450))
    assert a.science_hash() == b.science_hash() != c.science_hash()


def test_deep_merge_replaces_lists_and_clears_with_none():
    merged = deep_merge({"k": {"grid": [1, 1, 1], "spacing": 0.2}, "x": 1}, {"k": {"spacing": None}})
    assert merged == {"k": {"grid": [1, 1, 1], "spacing": None}, "x": 1}


def test_convergence_campaign_expands_to_expected_runs(campaigns):
    planned = expand_campaign(load_campaign(campaigns / "stage1_convergence.yaml"))
    ids = [p.config.run_id for p in planned]
    assert len(ids) == 30 and ids[0] == "Y_stage1_ref" and "Zr_stage1_kspacing0.07" in ids
    ref = planned[0].config
    assert ref.run.sweep.parameter == "reference" and ref.vasp.incar["ENCUT"] == 500
    encut = next(p.config for p in planned if p.config.run_id == "Y_stage1_encut300")
    assert encut.vasp.incar["ENCUT"] == 300 and encut.vasp.kpoints.spacing == 0.11
    # Shared physics comes from common_settings.yaml.
    assert encut.vasp.incar["SIGMA"] == 0.2 and encut.potcars["Y"] == "Y_sv"


def test_all_production_campaigns_plan_once_settings_are_filled(campaigns):
    expected = {
        "stage1_relax.yaml": {"Y_stage1_relax", "Zr_stage1_relax"},
        "stage2_h_energetics.yaml": {
            "Y_stage2_host",
            "Y_stage2_hT",
            "Y_stage2_hO",
            "Zr_stage2_host",
            "Zr_stage2_hT",
            "Zr_stage2_hO",
            "H2_stage2_molecule",
        },
        "stage3_vibrations.yaml": {
            "Y_stage3_vib_hT",
            "Y_stage3_vib_hO",
            "Zr_stage3_vib_hT",
            "Zr_stage3_vib_hO",
            "H2_stage3_vib_molecule",
        },
        "stage4_hydrides.yaml": {"Y_stage4_hydride", "Zr_stage4_hydride"},
        "stage4_hydride_vibrations.yaml": {"Y_stage4_vib_hydride", "Zr_stage4_vib_hydride"},
    }
    for name, ids in expected.items():
        planned = {p.config.run_id: p.config for p in expand_campaign(load_campaign(campaigns / name))}
        assert set(planned) == ids, name
    stage2 = {p.config.run_id: p.config for p in expand_campaign(load_campaign(campaigns / "stage2_h_energetics.yaml"))}
    assert stage2["Zr_stage2_hT"].structure.lattice_from_run == "Zr_stage1_relax"
    assert stage2["Zr_stage2_hT"].vasp.incar["ENCUT"] == 520 and stage2["Zr_stage2_hT"].vasp.kpoints.spacing == 0.15
    h2 = stage2["H2_stage2_molecule"]
    assert h2.vasp.kpoints.grid == (1, 1, 1) and h2.vasp.kpoints.spacing is None and h2.vasp.incar["ISMEAR"] == 0
    vib = {p.config.run_id: p.config for p in expand_campaign(load_campaign(campaigns / "stage3_vibrations.yaml"))}
    assert vib["Y_stage3_vib_hO"].dependencies() == ["Y_stage2_hO"]


def test_unfilled_placeholders_stop_planning():
    from hydrogen_solubility.paths import REPO_ROOT

    with pytest.raises(PlanError, match="placeholder"):
        expand_campaign(load_campaign(REPO_ROOT / "configs" / "campaigns" / "stage2_h_energetics.yaml"))


def test_tag_suffix_and_stale_config_removal(campaigns, tmp_path):
    out = tmp_path / "generated"
    _, planned, removed = write_plan(campaigns / "stage1_relax.yaml", out)
    assert {p.name for p in out.glob("*.yaml")} == {"Y_stage1_relax.yaml", "Zr_stage1_relax.yaml"}
    text = (campaigns / "stage1_relax.yaml").read_text().replace("stage: stage1\n", "stage: stage1\ntag: v2\n")
    (campaigns / "stage1_relax.yaml").write_text(text)
    _, planned, removed = write_plan(campaigns / "stage1_relax.yaml", out)
    assert {p.config.run_id for p in planned} == {"Y_stage1_relax_v2", "Zr_stage1_relax_v2"}
    assert {p.name for p in removed} == {"Y_stage1_relax.yaml", "Zr_stage1_relax.yaml"}


def test_unknown_campaign_keys_are_errors(campaigns):
    campaign = load_campaign(campaigns / "stage1_relax.yaml")
    campaign["runs"][0]["incar"] = {"ENCUT": 1}
    with pytest.raises(PlanError, match="unknown keys"):
        expand_campaign(campaign)
