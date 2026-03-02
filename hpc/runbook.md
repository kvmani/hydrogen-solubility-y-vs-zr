# HPC + VASP Runbook (Dry-Run-First, Slurm)

This runbook is cluster-agnostic and assumes VASP execution on an HPC using Slurm.

## 0) New To VASP?
Start with `hpc/beginner_vasp_tutorial.md` first.
If module names are unknown on your cluster, run `hpc/vasp_module_discovery_tutorial.md` before this runbook.

## 1) Prerequisites
- You have a validated stage config in `configs/`.
- You have read access to VASP executable and pseudopotentials on your cluster.
- You know your real Slurm `partition` and `account` values.
- You can run project scripts from repo root.

Core scripts:
- `tools/hpc/run_vasp_pipeline.sh`
- `tools/hpc/run_vasp_batch.sh`
- `tools/hpc/submit_vasp_job.sh`

## 2) One-Time Setup (Local or Frontend Node)
1. Discover module names (if unknown):
   - `tools/hpc/discover_vasp_modules.sh --keyword vasp`
2. Verify VASP environment first:
   - `tools/hpc/check_vasp_installation.sh --module <compiler_module> --module <mpi_module> --module <vasp_module>`
   - optional smoke: `tools/hpc/check_vasp_installation.sh --module <compiler_module> --module <mpi_module> --module <vasp_module> --run-smoke true --potcar /path/to/POTCAR --launch-cmd "srun -n 1"`
3. Install Python deps:
   - `pip install -r requirements.txt`
4. Validate baseline configs:
   - `python tools/validate_config.py configs/stage1_y_host_validation_v1.yaml configs/stage1_zr_host_validation_v1.yaml`
5. Edit config placeholders before real submission:
   - replace `hpc.partition: "<partition>"`
   - replace `hpc.account: "<account>"`

## 3) Initialize A Run Directory
For one config:
- `python tools/init_run.py configs/stage1_y_host_validation_v1.yaml`

Expected layout:
- `results/runs/<run_id>/inputs/`
- `results/runs/<run_id>/raw/`
- `results/runs/<run_id>/logs/`
- `results/runs/<run_id>/manifest.json`
- `results/runs/<run_id>/metrics.json`

## 4) Prepare Input Deck In `inputs/`
Minimum expected files for submit:
- `POSCAR`
- `KPOINTS`
- `INCAR`
- `POTCAR`

Helpful options:
- Auto-copy a baseline INCAR template via pipeline:
  - `--incar-template relax` or `--incar-template static`
- Or use a custom INCAR:
  - `--incar-path /absolute/path/to/INCAR`

Note:
- `POTCAR` is usually not versioned in git. Place it manually in `results/runs/<run_id>/inputs/POTCAR`.

## 5) Frontend Dry-Run (No Scheduler Submission)
Use this first for every new config or pipeline change.

Example:
```bash
tools/hpc/run_vasp_pipeline.sh \
  --mode dryrun \
  --config configs/stage1_y_host_validation_v1.yaml \
  --incar-template relax
```

What dry-run does:
- validates config
- ensures run folder exists
- checks input readiness (warns on missing files)
- syncs available inputs to `raw/`
- renders sbatch script in `logs/slurm/`
- syntax-checks rendered sbatch script (`bash -n`)
- appends execution event into `manifest.json`

What dry-run does not do:
- no Slurm submission
- no VASP execution

## 6) Frontend Smoke Test (Still No Real VASP Job)
Use smoke mode after dry-run and before submit.

Example:
```bash
tools/hpc/run_vasp_pipeline.sh \
  --mode smoke \
  --config configs/stage1_y_host_validation_v1.yaml \
  --compiler-module <compiler_module> \
  --mpi-module <mpi_module> \
  --vasp-module <vasp_module>
```

What smoke mode adds:
- executes rendered sbatch script locally with `VASP_PIPELINE_SMOKE_ONLY=1`
- exits before VASP launch
- optionally runs `sbatch --test-only` when available

If your cluster does not support `--test-only`, the script logs a warning and continues.

## 7) Real Slurm Submission
Submit only after dry-run and smoke pass.

Example:
```bash
tools/hpc/run_vasp_pipeline.sh \
  --mode submit \
  --config configs/stage1_y_host_validation_v1.yaml \
  --compiler-module <compiler_module> \
  --mpi-module <mpi_module> \
  --vasp-module <vasp_module> \
  --require-potcar true
```

Submit behavior:
- hard-fails if `partition/account` still look like placeholders
- hard-fails if required inputs are missing
- submits rendered sbatch via `tools/hpc/submit_vasp_job.sh`
- records parsed job ID (if available) into `manifest.json`
- writes submission receipt in orchestrator session log folder

## 8) Batch Orchestration Across Multiple Configs
Dry-run batch example:
```bash
tools/hpc/run_vasp_batch.sh \
  --mode dryrun \
  configs/stage1_y_host_validation_v1.yaml \
  configs/stage1_zr_host_validation_v1.yaml
```

Submit batch and continue even if one run fails:
```bash
tools/hpc/run_vasp_batch.sh \
  --mode submit \
  --continue-on-error true \
  configs/stage1_y_host_validation_v1.yaml \
  configs/stage1_zr_host_validation_v1.yaml
```

Batch output:
- TSV summary under `results/batch_runs/`

## 9) Logging And Diagnostics (Root-Cause First)
Per-run diagnostic locations:
- orchestrator sessions: `results/runs/<run_id>/logs/orchestrator/<timestamp>_<mode>/`
- rendered sbatch scripts: `results/runs/<run_id>/logs/slurm/`
- scheduler logs: `results/runs/<run_id>/logs/slurm/slurm-<jobid>.out|err`
- VASP stdout/err: `results/runs/<run_id>/raw/vasp.out|vasp.err`

Quick triage order:
1. `pipeline.log` for orchestration/preflight failure point.
2. `slurm-<jobid>.err` for scheduler/module/runtime errors.
3. `raw/OUTCAR` and `raw/OSZICAR` for VASP convergence/runtime details.
4. `manifest.json` `execution_events` for timeline and job metadata.

## 10) Post-Run Parsing
After run completion:
- `python tools/extract_metrics.py --run-dir results/runs/<run_id>`

Then verify:
- `metrics.json` updated with parsed energies/check flags.
- convergence and anomalies recorded in your progress log.

## 11) Common Failure Modes
- Missing `POTCAR` in submit mode:
  - place `POTCAR` in `inputs/`, rerun dry-run, then submit.
- Placeholder `partition/account`:
  - update config with real values, rerun dry-run/smoke.
- `sbatch --test-only` not supported:
  - rely on local smoke mode + `bash -n` result.
- Module command unavailable in shell:
  - test module setup in login shell, then set explicit module names in pipeline args.
