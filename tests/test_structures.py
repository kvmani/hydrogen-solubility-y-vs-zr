import math

import pytest

from hydrogen_solubility import structures as st

A, C_IDEAL = 3.2, 3.2 * math.sqrt(8.0 / 3.0)


@pytest.mark.parametrize(
    ("site", "coordination", "distance_over_a"),
    [("tetrahedral", 4, math.sqrt(3.0 / 8.0)), ("octahedral", 6, 1.0 / math.sqrt(2.0))],
)
def test_interstitial_site_geometry(site, coordination, distance_over_a):
    cell = st.hcp_supercell("Zr", A, C_IDEAL, (3, 3, 2), site)
    h = cell.natoms - 1
    distances = cell.neighbor_distances(h, "Zr")
    assert distances[:coordination] == pytest.approx([distance_over_a * A] * coordination, rel=1e-9)
    assert distances[coordination] > distances[0] * 1.3
    assert st.classify_h_site(cell) == site


def test_site_multiplicities_match_thermo():
    # 4 T and 2 O sites per 2-atom cell -> 2 and 1 per metal atom.
    assert len(st.HCP_TETRAHEDRAL_FRAC) / len(st.HCP_METAL_FRAC) == 2
    assert len(st.HCP_OCTAHEDRAL_FRAC) / len(st.HCP_METAL_FRAC) == 1


def test_all_tetrahedral_positions_are_tetrahedral():
    prim = st.make_supercell(st.hcp_primitive("Y", A, C_IDEAL), (3, 3, 2))
    for frac in st.HCP_TETRAHEDRAL_FRAC:
        h = tuple(f / n for f, n in zip(frac, (3, 3, 2)))
        d = sorted(prim.distance_frac(h, p) for p in prim.frac)
        assert d[:4] == pytest.approx([math.sqrt(3 / 8) * A] * 4)


def test_poscar_round_trip_with_selective_dynamics():
    cell = st.hcp_supercell("Y", 3.65, 5.73, (2, 2, 1), "octahedral").with_free_species(["H"])
    parsed = st.Structure.from_poscar(cell.to_poscar())
    assert parsed.species_order == ["Y", "H"]
    assert parsed.count("H") == 1 and parsed.count("Y") == 8
    assert parsed.volume == pytest.approx(cell.volume)
    assert parsed.selective[-1] == (True, True, True)
    assert parsed.selective[0] == (False, False, False)


def test_cartesian_poscar_is_converted():
    text = "test\n1.0\n4 0 0\n0 4 0\n0 0 4\nH\n2\nCartesian\n0 0 0\n1 2 3\n"
    s = st.Structure.from_poscar(text)
    assert s.frac[1] == pytest.approx((0.25, 0.5, 0.75))


def test_hcp_lattice_parameters_and_rejection():
    assert st.hcp_lattice_parameters(st.hcp_primitive("Y", 3.647, 5.731)) == pytest.approx((3.647, 5.731))
    with pytest.raises(st.StructureError):
        st.hcp_lattice_parameters(st.fluorite_dihydride("Y", 5.2))


def test_fluorite_hydrogen_is_tetrahedral():
    cell = st.fluorite_dihydride("Y", 5.2)
    assert cell.count("H") == 8 and cell.count("Y") == 4
    first_h = cell.species.index("H")
    assert cell.neighbor_distances(first_h, "Y")[:4] == pytest.approx([5.2 * math.sqrt(3) / 4] * 4)


@pytest.mark.parametrize("cell", ["primitive", "supercell", "hydride"])
def test_spacing_rule_is_respected_for_any_cell(cell):
    build = {
        "primitive": lambda: st.hcp_primitive("Zr", 3.23, 5.15),
        "supercell": lambda: st.make_supercell(st.hcp_primitive("Zr", 3.23, 5.15), (3, 3, 2)),
        "hydride": lambda: st.fluorite_dihydride("Zr", 4.78),
    }[cell]()
    grid = st.kpoint_grid_for_spacing(build, 0.15)
    assert st.kpoint_spacing_of_grid(build, grid) <= 0.15
    # ...and it is the smallest such grid: one fewer point on any axis breaks the rule.
    for axis in range(3):
        if grid[axis] > 1:
            coarser = list(grid)
            coarser[axis] -= 1
            assert st.kpoint_spacing_of_grid(build, coarser) > 0.15
