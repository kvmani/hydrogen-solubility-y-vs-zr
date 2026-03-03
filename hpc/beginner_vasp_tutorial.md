# Beginner Tutorial: Running VASP on Slurm HPC (Safely)

This tutorial is written for first-time VASP users and follows this project’s safety policy:
`check environment -> dry-run -> smoke -> submit real jobs`.

Before this tutorial, read: `docs/vasp_primer.md`.

## 0) What You Need Before You Start
- Access to an HPC account with VASP license entitlement.
- A known module stack (compiler, MPI, VASP module names).
- Read access to pseudopotentials (POTCAR source).
- Basic terminal usage and Slurm commands (`squeue`, `sbatch`, `sacct`).

If you do not know module names yet, do this first: `hpc/vasp_module_discovery_tutorial.md`.

## 1) Understand the 4 Core VASP Inputs
- `POSCAR`: crystal structure and atomic positions.
- `POTCAR`: pseudopotential data for each element in POSCAR order.
- `KPOINTS`: Brillouin-zone sampling mesh.
- `INCAR`: calculation settings (ENCUT, EDIFF, relaxation/static mode, etc.).

If one is missing or inconsistent, the run fails.

## 2) Discover VASP Modules (if module names are unknown)
Run on frontend/login node:

```bash
tools/hpc/discover_vasp_modules.sh --keyword vasp
```

Then inspect the generated report and pick candidate module triplets (compiler/MPI/VASP).

## 3) Verify VASP Is Installed (Quick Check)
Run on frontend/login node:

```bash
tools/hpc/check_vasp_installation.sh \
  --module <compiler_module> \
  --module <mpi_module> \
  --module <vasp_module> \
  --vasp-binary vasp_std
```

What this checks:
- module loading works
- `vasp_std` is in `PATH`
- shared libraries are resolved (via `ldd`/`otool`)
- optional `--version` probe

## 4) Optional Tiny Smoke Run (Best Confidence)
Use a minimal static test to ensure VASP actually executes.

```bash
tools/hpc/check_vasp_installation.sh \
  --module <compiler_module> \
  --module <mpi_module> \
  --module <vasp_module> \
  --run-smoke true \
  --potcar /path/to/POTCAR \
  --launch-cmd "srun -n 1" \
  --workdir /scratch/$USER/vasp_smoke_check
```

Notes:
- POTCAR must match the test element used by the script (Al).
- If login-node execution is blocked on your cluster, run this in an interactive Slurm allocation.

## 5) Project Workflow (Dry-Run First)
After VASP environment is healthy, use the project pipeline.

### 5.1 Generate Stage-1 campaign configs
```bash
make plan-stage1
```

### 5.2 Dry-run all campaign configs (no real compute)
```bash
tools/hpc/run_vasp_batch.sh --mode dryrun configs/generated/<campaign_dir>/*.yaml
```

### 5.3 Fill run input decks
For each run folder under `results/runs/<run_id>/inputs/`, provide:
- `POSCAR`
- `KPOINTS`
- `INCAR` (or use template sync)
- `POTCAR`

### 5.4 Smoke mode (checks job scripts without launching real VASP)
```bash
tools/hpc/run_vasp_batch.sh \
  --mode smoke \
  --compiler-module <compiler_module> \
  --mpi-module <mpi_module> \
  --vasp-module <vasp_module> \
  configs/generated/<campaign_dir>/*.yaml
```

### 5.5 Submit real jobs
```bash
tools/hpc/run_vasp_batch.sh \
  --mode submit \
  --continue-on-error true \
  --compiler-module <compiler_module> \
  --mpi-module <mpi_module> \
  --vasp-module <vasp_module> \
  configs/generated/<campaign_dir>/*.yaml
```

## 6) Monitor Jobs
- Queue state:
  - `squeue -u $USER`
- Historical status:
  - `sacct -j <job_id> --format=JobID,State,Elapsed,ExitCode`

## 7) Where to Look When Something Fails
Check in this order:
1. `results/runs/<run_id>/logs/orchestrator/<timestamp>_<mode>/pipeline.log`
2. `results/runs/<run_id>/logs/slurm/slurm-<jobid>.err`
3. `results/runs/<run_id>/raw/vasp.err`
4. `results/runs/<run_id>/raw/OUTCAR`
5. `results/runs/<run_id>/manifest.json` (`execution_events` timeline)

## 8) First-Time Mistakes to Avoid
- Submitting before dry-run and smoke checks.
- Using placeholder `partition`/`account` values in config.
- POTCAR order not matching POSCAR species order.
- Comparing Y vs Zr runs with different convergence settings.

## 9) Minimal Safe Starter Sequence
If you do nothing else, run this order:
1. `tools/hpc/discover_vasp_modules.sh --keyword vasp` (find module names)
2. `tools/hpc/check_vasp_installation.sh ...` (quick check)
3. `tools/hpc/check_vasp_installation.sh --run-smoke true ...` (optional but recommended)
4. `make plan-stage1`
5. batch `dryrun`
6. batch `smoke`
7. batch `submit`
