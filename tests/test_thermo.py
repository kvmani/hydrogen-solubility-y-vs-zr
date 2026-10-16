import math

import pytest

from hydrogen_solubility import thermo

# NIST Chemistry WebBook Shomate coefficients for H2(g): (A, B, C, D, E, G) for 298-1000 K and 1000-2500 K.
SHOMATE = {
    "low": (33.066178, -11.363417, 11.432816, -2.772874, -0.158558, 172.707974),
    "high": (18.563083, 12.257357, -2.859786, 0.268238, 1.977990, 156.288133),
}


def shomate_entropy(temperature):
    a, b, c, d, e, g = SHOMATE["low" if temperature <= 1000 else "high"]
    t = temperature / 1000.0
    return a * math.log(t) + b * t + c * t * t / 2 + d * t**3 / 3 - e / (2 * t * t) + g


@pytest.mark.parametrize("temperature", [298.15, 400, 600, 800, 1000, 1200])
def test_h2_gas_model_matches_nist_entropy(temperature):
    model = thermo.h2_entropy_J_mol_K(temperature)
    assert model == pytest.approx(shomate_entropy(temperature), rel=5e-3)


def test_nist_reference_value_itself():
    assert shomate_entropy(298.15) == pytest.approx(130.68, abs=0.01)


def test_zero_point_energy_and_high_temperature_limit():
    assert thermo.zero_point_energy([100.0, 200.0]) == pytest.approx(0.15)
    # Classical limit: F -> kT ln(hw/kT) when kT >> hw.
    t, hw = 5000.0, 10.0
    assert thermo.harmonic_free_energy([hw], t) == pytest.approx(
        thermo.K_B * t * math.log(hw * 1e-3 / (thermo.K_B * t)), abs=2e-4
    )


def test_sieverts_square_root_law_in_dilute_limit():
    dg = {"tetrahedral": 0.6}
    t = 600.0
    x1 = thermo.concentration(dg, thermo.delta_mu_h(t, 1.0e3), t)
    x4 = thermo.concentration(dg, thermo.delta_mu_h(t, 4.0e3), t)
    assert x1 < 1e-3 and x4 / x1 == pytest.approx(2.0, rel=1e-3)


def test_occupancy_limits_and_site_multiplicity():
    assert thermo.occupancy(-10.0, 0.0, 300.0) == pytest.approx(1.0)
    assert thermo.occupancy(10.0, 0.0, 300.0) == pytest.approx(0.0, abs=1e-100)
    # Saturating both site types gives 2 T + 1 O = 3 H per metal atom.
    assert thermo.concentration({"tetrahedral": -5.0, "octahedral": -5.0}, 0.0, 300.0) == pytest.approx(3.0)


def test_plateau_pressure_is_where_gas_matches_hydride():
    t, g_hyd = 700.0, -0.45
    p = thermo.plateau_pressure(g_hyd, t)
    assert thermo.delta_mu_h(t, p) == pytest.approx(g_hyd, abs=1e-9)


def test_weight_ppm_conversion():
    # 1 H per 1000 Zr atoms ~ 11 wppm.
    assert thermo.atomic_ratio_to_wppm(1e-3, "Zr") == pytest.approx(11.05, rel=1e-3)
