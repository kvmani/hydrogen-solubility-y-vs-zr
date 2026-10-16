# VASP Primer For This Project

This primer is for beginners who want to understand how VASP calculations are designed, executed, and analyzed before using the advanced orchestration scripts in this repository.

If you want the more project-specific DFT theory, read [`docs/dft_introduction.md`](dft_introduction.md). If you want the practical run path, read [Workflow](workflow.md).

## 1) What VASP Is (Philosophy + Modeling Assumptions)
VASP solves the electronic structure problem for periodic solids using Kohn-Sham density functional theory (DFT) with a plane-wave basis and pseudopotential/PAW datasets.

Core philosophy:
- Replace the many-electron problem with an effective one-electron problem (Kohn-Sham DFT).
- Represent wavefunctions in a plane-wave basis (controlled mainly by `ENCUT`).
- Use periodic boundary conditions (your simulation cell is repeated infinitely).
- Use Brillouin-zone sampling (`KPOINTS`) for reciprocal-space integration.
- Iterate until self-consistency in charge density and total energy.

What this means in practice:
- Numerical settings are part of the scientific method, not just technical details.
- Energies are only comparable if settings are consistent across compared systems.
- Convergence testing is mandatory before drawing physical conclusions.

## 2) How A Typical VASP Study Is Structured
A robust VASP study usually has 4 phases:

1. Preprocessing:
- Build/validate crystal structures.
- Choose functional, pseudopotentials, cutoff, and k-mesh strategy.
- Decide which quantities you need (energy, forces, DOS, migration barrier, etc.).

2. Baseline/convergence:
- Test sensitivity to `ENCUT` and k-mesh.
- Confirm energy/force stability against tighter settings.

3. Production calculations:
- Run the scientifically relevant cases with frozen, validated settings.
- Keep full provenance (config, script, environment, logs, git state).

4. Post-processing + analysis:
- Parse outputs (`OUTCAR`, `OSZICAR`, etc.).
- Compute derived quantities and compare cases consistently.
- Document uncertainty, caveats, and remaining gaps.

This repo enforces this structure via config-driven workflows and stage gates.

## 3) The 4 Essential VASP Inputs
Every run depends on consistent input files:

- `POSCAR`:
  - lattice vectors, species order, atom counts, and coordinates.
  - species order must match `POTCAR` order.

- `POTCAR`:
  - pseudopotential/PAW datasets for each element.
  - choose variants intentionally (`_sv`, `_pv`, etc.) and record them in provenance.

- `KPOINTS`:
  - reciprocal-space mesh or path.
  - metals generally need careful k-point convergence.

- `INCAR`:
  - run controls (`ENCUT`, `EDIFF`, `ISMEAR`, `IBRION`, `NSW`, etc.).
  - incorrect INCAR settings are the most common beginner failure source.

## 4) Preprocessing Checklist (Beginner Practical)
Before launching any expensive run:

1. Verify structure sanity:
- no overlapping atoms
- realistic lattice/volume
- correct composition and phase label

2. Lock comparison strategy:
- same functional and pseudopotential policy for Y vs Zr
- same convergence logic and tolerances

3. Choose run type:
- relaxation (`NSW > 0`, ionic updates active)
- static single-point (`NSW = 0`, `IBRION = -1`)

4. Choose smearing appropriately:
- metallic systems often start with finite smearing (`ISMEAR=1`, non-zero `SIGMA`) for relaxations
- final static energies may use a different choice if scientifically justified

5. Confirm consistency:
- `POSCAR` species order == `POTCAR` order
- k-mesh and `ENCUT` values are part of your convergence campaign design

## 5) Running VASP On HPC (How It Actually Executes)
On clusters, VASP runs inside a Slurm job: the job loads modules (compiler, MPI, VASP) and starts
the binary through an MPI launcher, e.g. `srun vasp_std`. In this repository you never write that
job script yourself:

1. Find and verify the VASP modules once: [HPC Setup](hpc_setup.md).
2. Put them into `configs/site.yaml`.
3. `./hsol run` renders the job script for each run and enforces `dryrun -> smoke -> submit`
   ([Workflow](workflow.md)).

This prevents wasting queue time on avoidable setup errors.

## 6) Typical VASP Outputs And What They Mean
Common files you will inspect:

- `OUTCAR`:
  - detailed run log, energies, forces, stress, convergence behavior, warnings.
  - primary file for deep debugging.

- `OSZICAR`:
  - compact electronic/ionic iteration summary.
  - fast check for run progression and final energy.

- `CONTCAR`:
  - final geometry after relaxation.

- `vasp.out` / `vasp.err`:
  - shell-level stdout/stderr from job launcher.

- `CHGCAR`, `WAVECAR` (if enabled):
  - charge density and wavefunctions for reuse/analysis.

- `DOSCAR`, `EIGENVAL`, `PROCAR`, `vasprun.xml` (depending on settings):
  - electronic structure analysis outputs.

## 7) How To Judge If A Run Is Scientifically Usable
A job “finished” is not automatically “usable.”

Minimum acceptance checks:
- electronic convergence achieved (SCF reached target tolerance)
- ionic convergence achieved for relaxations (forces/stress at criteria)
- no severe warnings in `OUTCAR`
- no inconsistent settings versus the comparison set

Project-level acceptance adds:
- convergence campaign evidence (ENCUT/k-mesh)
- manifest/metrics/log provenance complete
- reproducible rerun path documented

## 8) Post-Processing In This Repository
`./hsol collect` (run automatically at the end of each job) parses `OUTCAR`, `OSZICAR` and
`CONTCAR` into `metrics.json`: energies, SCF and ionic convergence, forces, pressure, vibrational
modes and structure checks. It then refreshes the run's `report.html` and `results/INDEX.md`.
Provenance (inputs, hashes, git state, job history) lives in each run's `manifest.json`; see
[Data Model](data_model.md).

## 9) Analysis Pattern For Y vs Zr In Stage-1
1. `./hsol plan configs/campaigns/stage1_convergence.yaml`, then prepare, run and collect.
2. `./hsol analyze convergence` compares the energy per atom against the most accurate point of the
   ENCUT series and of the k-point-spacing series for each metal.
3. It recommends one ENCUT and one k-point spacing valid for both metals; you copy them into
   `configs/campaigns/converged_settings.yaml`, which every later stage uses.

Only after this should Stage-2 H-interstitial energetics begin.

## 10) Beginner Pitfalls
- Mixing incompatible settings across compared systems.
- Skipping convergence and trusting first-pass energies.
- Ignoring `OUTCAR` warnings because job exit code is 0.
- Treating module availability as proof that runtime is healthy.
- Submitting large batches before dry-run/smoke validation.

## 11) How This Primer Connects To Other Docs
1. This primer and [DFT Introduction](dft_introduction.md): concepts.
2. [Scheme](scheme.md): which calculations the project needs and why.
3. [HPC Setup](hpc_setup.md) and [Workflow](workflow.md): how to run them.
