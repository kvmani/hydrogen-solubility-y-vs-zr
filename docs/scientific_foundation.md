# Scientific Foundation

This project is not just a runbook for VASP. It is a thermodynamic explanation project: we want to identify which energetic terms make hydrogen easier to dissolve in yttrium than in zirconium, and to quantify how those terms map into observable solubility curves.

## The Core Thermodynamic Question

Let $x_H$ denote the hydrogen occupancy of the relevant interstitial lattice sites in the host metal. In the dilute limit, the project assumes that the hydrogen chemical potential in the solid is determined by three pieces:

1. a 0 K insertion energy from electronic structure,
2. a vibrational free-energy correction,
3. configurational entropy and, where needed, non-ideal interactions.

The simplest regular-solution form is

$$
G(x_H, T) = N_s \left[
x_H \Delta g_{\mathrm{sol}}(T)
+ k_B T \left(x_H \ln x_H + (1 - x_H)\ln(1 - x_H)\right)
+ \Omega x_H (1 - x_H)
 \right]
$$

where $N_s$ is the number of available sites, $\Delta g_{\mathrm{sol}}(T)$ is the single-site solution free energy, and $\Omega$ is an effective interaction parameter for deviations from ideal dilute behavior.

The corresponding hydrogen chemical potential in the solid is

$$
\mu_H^{\mathrm{solid}} =
\frac{\partial G}{\partial N_H}
= \Delta g_{\mathrm{sol}}(T)
+ k_B T \ln \frac{x_H}{1 - x_H}
+ \Omega(1 - 2x_H).
$$

At equilibrium with molecular hydrogen,

$$
\mu_H^{\mathrm{solid}}(T, x_H) = \tfrac{1}{2}\mu_{H_2}^{\mathrm{gas}}(T, p).
$$

If $x_H \ll 1$ and $\Omega \approx 0$, then the lattice-gas form reduces to the familiar square-root pressure law

$$
x_H \propto p^{1/2}\exp\left[-\frac{\Delta g_{\mathrm{sol}}(T)}{k_B T}\right].
$$

That is the mathematical reason the project tracks both a free-energy scale and a pressure scale. A static energy difference alone is not enough to explain the measured contrast between Y and Zr. The finite-temperature terms matter.

## DFT Solution Energy

The code computes a host-plus-hydrogen insertion energy of the form

$$
\Delta E_{\mathrm{sol}} =
E_{\mathrm{tot}}(\text{host}+H) - E_{\mathrm{tot}}(\text{host}) - \tfrac{1}{2}E_{\mathrm{tot}}(H_2),
$$

or an equivalent reference-formulation chosen consistently across all comparisons.

The finite-temperature solution free energy is then written as

$$
\Delta G_{\mathrm{sol}}(T)
= \Delta E_{\mathrm{sol}}
+ \Delta F_{\mathrm{vib}}(T)
+ \Delta F_{\mathrm{el}}(T)
+ \Delta F_{\mathrm{q}}(T),
$$

where the extra terms are vibrational, electronic, and any remaining small corrections. In the present project, the vibrational term is expected to be the leading correction beyond the DFT total-energy difference for hydrogen-bearing states.

The vibrational free energy of a harmonic mode set is

$$
F_{\mathrm{vib}}(T) = \sum_i \left[
\tfrac{1}{2}\hbar\omega_i +
k_B T \ln\left(1 - e^{-\hbar\omega_i / k_B T}\right)
 \right].
$$

This is the baseline expression that stage-3 calculations will use when the project expands beyond host validation.

## Hydride Competition

Hydrogen solubility is not controlled by the dilute interstitial state alone. Once a hydride phase becomes thermodynamically preferable, the dilute solution window closes.

The precipitation criterion can be written generically as

$$
\Delta G_{\mathrm{hydride}}(T, p)
= G(\mathrm{MH}_y, T) - G(\mathrm{M}, T) - \tfrac{y}{2}\mu_{H_2}^{\mathrm{gas}}(T, p),
$$

where \(M\) is Y or Zr. If the hydride free energy becomes negative relative to the host-plus-gas reference, the system prefers hydride formation over continued dilute dissolution.

This is the thermodynamic reason the Zr system is expected to truncate the dilute regime earlier than Y. The experimental phase assessments in the literature support that qualitative difference, and the project’s goal is to quantify it from first principles rather than assume it.

## What Must Be Computed

The project’s scientific model needs four outputs:

1. host reference energies for alpha-Y and alpha-Zr,
2. dilute-H site energies and site hierarchy,
3. vibrational corrections for host and host-plus-H states,
4. competing hydride free energies and phase windows.

That chain is what eventually converts VASP energies into a prediction for $c_H(T, p)$.

## Why The Comparison Matters

The literature already tells us the empirical story:

- Y can hold substantially more hydrogen than Zr in the relevant temperature range.
- Zr exhibits strong terminal-solubility limitations and hydride precipitation.
- Both systems require a proper thermodynamic treatment, not only a chemistry intuition.

The project exists to turn those statements into a reproducible, equation-level explanation with explicit provenance.

## Method References

The electronic-structure baseline uses the standard PBE + PAW + VASP method stack, which is documented in the canonical method papers for the exchange-correlation functional, the PAW formalism, and the VASP iterative solver family :cite:p:`perdew1996_pbe,blochl1994_paw,kresse1996_iterative,kresse1999_paw_vasp`.

The vibrational treatment follows standard lattice-dynamics references and tools :cite:p:`baroni2001_dfpt,parlinski1997_finite_displacement,togo2015_phonopy,fultz2010_vibrational_thermo`.

The thermodynamic framework for hydrogen in interstitial solids follows the classical solubility and interstitial-solution literature :cite:p:`lacher1937_solubility_formula,hashino1976_interstitial_thermo,flanagan1983_solvus`.

The project’s experimental anchor points for Y and Zr come from the curated literature map in `literature/lit_review.md` and `literature/benchmarks/`.

## References

```{bibliography}
```
