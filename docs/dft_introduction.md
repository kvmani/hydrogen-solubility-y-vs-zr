# DFT Introduction For This Project

This page explains the theory behind density functional theory in the way this project actually uses it: as the electronic-structure engine that produces host and host-plus-hydrogen energies for the Y vs Zr solubility comparison.

It is written for beginners, but it does not omit the math. The goal is to make the assumptions visible so the later thermodynamic interpretation is defensible.

## Why DFT Is Used Here

The project needs a way to compare the relative stability of:

- alpha-Y and alpha-Zr host cells,
- the same host cells with hydrogen in candidate interstitial sites,
- competing hydride phases at the same reference level.

DFT is appropriate because it gives a first-principles approximation to the ground-state electronic energy without fitting directly to the system under study.

The method is not exact. Its value is that it is systematic, improvable, and comparable across both metals when the setup is kept identical.

## The Many-Electron Problem

The exact electronic structure of a material is governed by the many-body Schrodinger equation,

$$
\hat{H} \Psi = E \Psi,
$$

with

$$
\hat{H} =
\sum_i \left(-\frac{\hbar^2}{2m_e}\nabla_i^2 + V_{\mathrm{ext}}(\mathbf{r}_i)\right)
+ \sum_{i<j}\frac{e^2}{4\pi\epsilon_0 |\mathbf{r}_i-\mathbf{r}_j|}.
$$

This is too expensive to solve directly for the periodic solids in this project.

## The DFT Idea

Density functional theory replaces the wavefunction problem with a density problem. The central variable is the electron density $n(\mathbf{r})$, and the total energy is written as a functional of that density:

$$
E[n] = T_s[n] + \int V_{\mathrm{ext}}(\mathbf{r}) n(\mathbf{r})\,d\mathbf{r}
+ E_H[n] + E_{xc}[n].
$$

Here:

- $T_s[n]$ is the kinetic energy of a fictitious non-interacting system,
- $E_H[n]$ is the classical electron-electron Coulomb term,
- $E_{xc}[n]$ is the exchange-correlation functional,
- $V_{\mathrm{ext}}$ is the ionic potential from the nuclei and PAW datasets.

The exact exchange-correlation term is unknown. All practical DFT calculations make an approximation for it.

## Kohn-Sham Equations

The standard practical form is the Kohn-Sham system:

$$
\left[-\frac{\hbar^2}{2m_e}\nabla^2 + V_{\mathrm{eff}}(\mathbf{r})\right]\psi_i(\mathbf{r})
= \varepsilon_i \psi_i(\mathbf{r}),
$$

with

$$
V_{\mathrm{eff}}(\mathbf{r}) =
V_{\mathrm{ext}}(\mathbf{r}) + V_H(\mathbf{r}) + V_{xc}(\mathbf{r}).
$$

The density is rebuilt from the occupied orbitals:

$$
n(\mathbf{r}) = \sum_i f_i |\psi_i(\mathbf{r})|^2,
$$

where $f_i$ are occupation numbers.

The calculation is self-consistent because $V_{\mathrm{eff}}$ depends on $n(\mathbf{r})$, which depends on the $\psi_i$, which depend on $V_{\mathrm{eff}}$.

## Self-Consistency In Practice

The workflow is:

1. start with a trial density,
2. build $V_{\mathrm{eff}}$,
3. solve the Kohn-Sham equations,
4. update the density,
5. repeat until the change is small enough.

The project uses this self-consistent field loop as the basis for every reported energy.

For beginners, the key point is simple: if the calculation has not converged self-consistently, the reported energy is not trustworthy.

## Exchange-Correlation Approximation

This project uses PBE, a generalized-gradient approximation:

$$
E_{xc}^{\mathrm{PBE}}[n] \approx E_{xc}^{\mathrm{GGA}}[n, \nabla n].
$$

The approximation is a compromise between accuracy and computational cost. It is widely used for metallic materials and interstitial energetics because it is robust and well benchmarked.

The method papers for PBE, PAW, and VASP define the computational baseline used throughout the project [@perdew1996_pbe; @blochl1994_paw; @kresse1996_iterative; @kresse1999_paw_vasp].

## Periodic Solids, Supercells, And Why They Matter

In this project, the material is modeled as a periodic crystal. That means one finite cell is repeated infinitely in all directions.

For a host-only benchmark, the supercell must be large enough that periodic images of the defect or energy perturbation do not strongly interact. For hydrogen insertion, this is critical because a too-small cell can make one H atom interact with its own replicas.

That is why Stage-1 convergence and Stage-2 dilute-H work must use a controlled supercell strategy.

## Plane Waves And ENCUT

VASP expands orbitals in a plane-wave basis. A plane wave has the form

$$
e^{i\mathbf{G}\cdot\mathbf{r}},
$$

where $\mathbf{G}$ is a reciprocal-lattice vector.

The expansion is truncated by a kinetic-energy cutoff:

$$
\frac{\hbar^2 |\mathbf{G}|^2}{2m_e} \le E_{\mathrm{cut}}.
$$

In the input files, this is `ENCUT`.

Beginner takeaway:

- too low `ENCUT` gives inaccurate energies and forces,
- too high `ENCUT` increases runtime,
- the right choice is found by convergence testing, not guesswork.

## k-Point Sampling

Periodic solids require Brillouin-zone integration. In practice, the integral becomes a sum over k-points:

$$
\frac{1}{\Omega_{\mathrm{BZ}}}\int_{\mathrm{BZ}} f(\mathbf{k})\,d\mathbf{k}
\approx \sum_{\mathbf{k}} w_{\mathbf{k}} f(\mathbf{k}).
$$

The `KPOINTS` file controls this sampling.

For metallic systems like Y and Zr, k-point convergence is often as important as cutoff convergence. If the mesh is too coarse, the energy differences you care about can be buried in numerical noise.

## Why PAW Is Used

The project uses the projector augmented-wave method.

The PAW formalism reconstructs the all-electron character near the nuclei while keeping the smooth plane-wave representation efficient in the valence region. This is one reason PAW is attractive for transition metals and interstitial hydrogen studies.

The core PAW idea is the transformation between a smooth pseudo-wavefunction and a more accurate all-electron-like wavefunction in augmentation regions. The formalism is standard in VASP and is part of the method stack cited above.

## What DFT Gives The Project

For this repository, DFT is used to compute:

- host total energies,
- relaxed geometries,
- hydrogen site energies,
- relative stability between candidate interstitial configurations,
- reference energies for later thermodynamic mapping.

Those quantities are not yet the final solubility answer. They are the energetic inputs to the later free-energy model.

## Critical Limitations

Beginners often overinterpret DFT results. The main limitations relevant here are:

- DFT gives a 0 K electronic baseline unless corrections are added.
- Finite-size effects can bias defect energies if the cell is too small.
- Different pseudopotentials or cutoffs can change relative energies.
- Metallic smearing choices can influence convergence behavior.
- DFT does not directly give concentration-vs-temperature solubility without thermodynamic post-processing.

This is why the project separates:

1. electronic-structure calculation,
2. vibrational correction,
3. thermodynamic mapping.

## Minimal Mental Model For Beginners

If you only remember five things, remember these:

1. DFT approximates the electronic ground state from the electron density.
2. `ENCUT`, `KPOINTS`, and pseudopotentials control numerical quality.
3. Self-consistency must be achieved before trusting energies.
4. Relative energies are meaningful only when the setup is consistent.
5. Solubility requires free-energy modeling, not just a single DFT total energy.

## References

```{bibliography}
```
