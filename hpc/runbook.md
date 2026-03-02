# HPC + VASP Runbook (Beginner Baseline)

## A. Pre-Run Checklist
- Define objective for this run (what quantity are you extracting?).
- Assign a `run_id` per `docs/conventions.md`.
- Prepare `results/runs/<run_id>/inputs/` and copy input templates.
- Record config path and planned convergence settings.

## B. Input Checklist
- Structure: POSCAR is validated (lattice, species, positions).
- Potentials: POTCAR choices documented in manifest.
- INCAR: start from `hpc/vasp_templates/INCAR.relax` or `INCAR.static`.
- KPOINTS: selected based on convergence strategy.

## C. Submission Checklist
- Copy and edit `hpc/slurm_templates/submit_vasp_generic.sbatch`.
- Confirm walltime, tasks, and loaded modules for your cluster.
- Submit with `sbatch` and log the returned job ID in manifest.

## D. Convergence Checklist
- Electronic convergence reached (`EDIFF` criterion).
- Ionic convergence reached for relax runs (`EDIFFG` + force thresholds).
- No unconverged or suspicious warnings in OUTCAR/OSZICAR.
- Energy cutoff and k-mesh sensitivity documented (where relevant).

## E. Post-Run Checklist
- Archive raw outputs in `results/runs/<run_id>/raw/`.
- Write/update `manifest.json` and `metrics.json`.
- Summarize key outcomes and blockers in `results/runs/<run_id>/report.html` (required in later tasks) and `progress/` log.

## F. High-Level Interpretation Guidance
- Compare site energies only after consistent convergence settings.
- Separate electronic energies from finite-temperature corrections.
- Distinguish dilute solution energetics from hydride-phase stability energetics.
