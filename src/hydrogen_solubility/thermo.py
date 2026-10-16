"""Thermodynamics used to turn DFT energies into hydrogen solubilities.

All energies are in eV, temperatures in K, pressures in Pa. The equations are
derived in ``docs/scheme.md``; in short, for interstitial site type ``s``:

    dg_s(T)   = dE_s + F_vib,s(T) - 1/2 F_vib,H2(T)          (per H, vs 1/2 H2)
    dmu_H     = 1/2 [mu_trans(T, p) + mu_rot(T)]               (H2 gas, ideal)
    theta_s   = 1 / (1 + exp[(dg_s - dmu_H) / kT])            (site occupancy)
    x_H       = sum_s n_s theta_s                              (H per metal atom)

and at the hydride solvus dmu_H is replaced by the hydride's per-H free energy.

The H2 gas is an ideal rigid rotor / harmonic oscillator. Its electronic and
vibrational parts come from DFT (E_H2 and the computed stretch frequency); only the
translational mass and the rotational constant are experimental inputs.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, Sequence

# CODATA 2018 exact/recommended constants.
K_B = 8.617333262e-5  # eV/K
K_B_J = 1.380649e-23  # J/K
H_PLANCK_J = 6.62607015e-34  # J s
AMU_KG = 1.66053906660e-27  # kg
EV_J = 1.602176634e-19  # J
N_A = 6.02214076e23  # 1/mol
HC_OVER_K_CM_K = 1.438776877  # second radiation constant, cm K

P_STANDARD = 1.0e5  # Pa (1 bar)

#: H2 inputs: mass (2 x 1H atomic mass) and rotational constant B_e = 60.853 cm^-1
#: (NIST Chemistry WebBook, constants of diatomic molecules, X 1Sigma_g+).
H2_MASS_AMU = 2 * 1.00782503207
H2_ROT_CONST_CM = 60.853
H2_SYMMETRY = 2
H2_THETA_ROT_K = HC_OVER_K_CM_K * H2_ROT_CONST_CM

#: Interstitial sites per metal atom in hcp (see structures.py).
SITES_PER_METAL: Dict[str, int] = {"tetrahedral": 2, "octahedral": 1}

#: Standard atomic weights (g/mol), for weight-ppm conversion.
ATOMIC_WEIGHT = {"H": 1.008, "Y": 88.906, "Zr": 91.224}


def harmonic_free_energy(modes_meV: Iterable[float], temperature: float) -> float:
    """Sum over modes of hw/2 + kT ln(1 - exp(-hw/kT)); equals the ZPE at T = 0."""

    total = 0.0
    for mode in modes_meV:
        hw = mode * 1e-3
        total += 0.5 * hw
        if temperature > 0:
            total += K_B * temperature * math.log1p(-math.exp(-hw / (K_B * temperature)))
    return total


def zero_point_energy(modes_meV: Iterable[float]) -> float:
    return harmonic_free_energy(modes_meV, 0.0)


def mu_translational(temperature: float, pressure: float, mass_amu: float = H2_MASS_AMU) -> float:
    """Ideal-gas translational chemical potential per molecule, -kT ln[(kT/p) / lambda^3]."""

    kt_j = K_B_J * temperature
    lam3 = (H_PLANCK_J**2 / (2.0 * math.pi * mass_amu * AMU_KG * kt_j)) ** 1.5
    return -K_B * temperature * math.log(kt_j / (pressure * lam3))


def mu_rotational(temperature: float, theta_rot: float = H2_THETA_ROT_K, symmetry: int = H2_SYMMETRY) -> float:
    """Rigid-rotor -kT ln q_rot with the Mulholland high-temperature expansion.

    q_rot = T/(sigma theta) [1 + theta/(3T) + theta^2/(15 T^2)], accurate to well below
    1 meV for H2 above ~200 K.
    """

    t = temperature
    q = t / (symmetry * theta_rot) * (1.0 + theta_rot / (3.0 * t) + theta_rot**2 / (15.0 * t * t))
    return -K_B * t * math.log(q)


def delta_mu_h(temperature: float, pressure: float) -> float:
    """Translational + rotational H2 chemical potential per H atom (excludes E_H2 and vibration)."""

    return 0.5 * (mu_translational(temperature, pressure) + mu_rotational(temperature))


def h2_entropy_J_mol_K(temperature: float, pressure: float = P_STANDARD, stretch_meV: float = 545.7) -> float:
    """Molar entropy of the model H2 gas, -d(mu)/dT, by central difference (for validation)."""

    def mu(t: float) -> float:
        return mu_translational(t, pressure) + mu_rotational(t) + harmonic_free_energy([stretch_meV], t)

    dt = 0.01
    return -(mu(temperature + dt) - mu(temperature - dt)) / (2 * dt) * EV_J * N_A


def occupancy(dg: float, dmu: float, temperature: float) -> float:
    """Fermi-Dirac-like lattice-gas occupancy of one site type (numerically stable)."""

    z = (dg - dmu) / (K_B * temperature)
    if z > 0:
        e = math.exp(-z)
        return e / (1.0 + e)
    return 1.0 / (1.0 + math.exp(z))


def concentration(site_dg: Dict[str, float], dmu: float, temperature: float) -> float:
    """H per metal atom: sum over site types of multiplicity x occupancy."""

    return sum(SITES_PER_METAL[site] * occupancy(dg, dmu, temperature) for site, dg in site_dg.items())


def plateau_pressure(dg_hydride: float, temperature: float) -> float:
    """H2 pressure at which gas, dilute solution and hydride coexist (Pa).

    Solves dmu_H(T, p) = dg_hydride using dmu_H(T, p) = dmu_H(T, p0) + kT/2 ln(p/p0).
    """

    exponent = 2.0 * (dg_hydride - delta_mu_h(temperature, P_STANDARD)) / (K_B * temperature)
    return P_STANDARD * math.exp(min(exponent, 700.0))


def atomic_ratio_to_wppm(x: float, metal: str) -> float:
    """Convert H/M atomic ratio to weight parts per million of H."""

    m_h, m_m = ATOMIC_WEIGHT["H"], ATOMIC_WEIGHT[metal]
    return 1.0e6 * x * m_h / (m_m + x * m_h)


def temperatures(start: float, stop: float, step: float) -> Sequence[float]:
    count = int(math.floor((stop - start) / step + 1e-9)) + 1
    return [start + i * step for i in range(count)]
