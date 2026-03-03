# VASP Primer For This Project

This primer is for beginners who want to understand how VASP calculations are designed, executed, and analyzed before using the advanced orchestration scripts in this repository.

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
On clusters, VASP is usually invoked through Slurm:
- load modules (compiler, MPI, VASP)
- launch with `srun ... vasp_std`

In this repository, use this order:

1. Module discovery (if needed):
- `tools/hpc/discover_vasp_modules.sh --keyword vasp`

2. Binary/health checks:
- `tools/hpc/check_vasp_installation.sh --module <compiler> --module <mpi> --module <vasp>`
- optional smoke run with POTCAR

3. Workflow execution:
- `dryrun` -> `smoke` -> `submit`
- scripts: `tools/hpc/run_vasp_pipeline.sh` and `tools/hpc/run_vasp_batch.sh`

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
Current automated parser:
- `python tools/extract_metrics.py --run-dir results/runs/<run_id>`

What gets captured now:
- key energies from `OUTCAR`/`OSZICAR`
- basic convergence flags
- standardized `metrics.json`

Where provenance lives:
- `results/runs/<run_id>/manifest.json`
- `results/runs/<run_id>/logs/...`

## 9) Analysis Pattern For Y vs Zr In Stage-1
For host-only baseline calculations:

1. Generate campaign configs (`make plan-stage1`).
2. Run dry-run/smoke/submit in batch.
3. Parse all completed runs to metrics.
4. Compare energy trends versus:
- `ENCUT`
- k-grid density
5. Select converged settings that satisfy tolerance for both systems.

Only after this should Stage-2 H-interstitial energetics begin.

## 10) Beginner Pitfalls
- Mixing incompatible settings across compared systems.
- Skipping convergence and trusting first-pass energies.
- Ignoring `OUTCAR` warnings because job exit code is 0.
- Treating module availability as proof that runtime is healthy.
- Submitting large batches before dry-run/smoke validation.

## 11) How This Primer Connects To Other Docs
Use this sequence:

1. This file: `docs/vasp_primer.md`
2. Module discovery: `hpc/vasp_module_discovery_tutorial.md`
3. Beginner run path: `hpc/beginner_vasp_tutorial.md`
4. Operator details: `hpc/runbook.md`
5. Stage-1 campaign execution: `docs/stage1_campaign.md`

Following this order is the fastest path from beginner status to reliable execution in this repository.
