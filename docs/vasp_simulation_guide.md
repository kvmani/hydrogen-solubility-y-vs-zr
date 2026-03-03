# VASP Simulation Guide: alpha-Y and alpha-Zr (Host + H Ground-State Workflow)

This guide is the practical, end-to-end procedure for launching and analyzing VASP calculations in this repository.

## 1) Goal And Objective

### Scientific goal
Build a reproducible DFT workflow to compare hydrogen energetics in alpha-Y and alpha-Zr, then explain the solubility contrast.

### Immediate computational objective
1. Stage-1: converge pure-host energies (alpha-Y and alpha-Zr).
2. Stage-2 (next): compute dilute-H interstitial ground-state energetics (tetrahedral and octahedral sites, plus symmetry-distinct variants if needed).

### Success criteria
- All runs are config-driven and reproducible (`manifest.json`, `metrics.json`, `report.html`, logs).
- Stage-1 convergence tolerance is met before Stage-2 production.
- Stage-2 site hierarchy (preferred H site) is established for both systems.

## 2) Planned Input Ranges And Run Matrix

## Stage-1 (already defined in configs)
Common settings for both systems:
- Systems: `Y`, `Zr`
- Phase: `alpha_hcp`
- Supercell: `4x4x3`
- Functional: `PBE`
- ENCUT scan: `400, 450, 520, 600 eV`
- k-point scan: `8x8x6`, `10x10x6`, `12x12x8`
- Baseline reference point: `ENCUT=520`, `k=12x12x8`
- Convergence target: `1.0 meV/atom`

Short meaning of each term:
- `Systems`: which chemical host metal is being simulated (`Y` or `Zr`).
- `Phase`: crystal structure type; `alpha_hcp` means hexagonal close-packed alpha phase.
- `Supercell`: repetition of the unit cell in 3 directions; `4x4x3` creates a larger periodic model.
- `Functional`: DFT exchange-correlation model; `PBE` is the chosen approximation.
- `ENCUT scan`: plane-wave cutoff-energy sweep to test basis-set convergence.
- `k-point scan`: Brillouin-zone sampling sweep to test reciprocal-space convergence.
- `Baseline reference point`: default numerical setting used as the central comparison run.
- `Convergence target`: maximum acceptable energy change after tightening settings (`1.0 meV/atom` here).

Cross references:
- Concept definitions: `docs/vasp_primer.md` (Sections 1, 2, 3).
- How these keys are represented in YAML: `docs/config_schema.md`.
- Stage-1 campaign usage in this repo: `docs/stage1_campaign.md`.

Planned campaign size from `tools/plan_stage1_campaign.py --sweeps both --include-reference`:
- Per system: 8 runs (1 reference + 4 ENCUT points + 3 k-point points)
- Total: 16 runs (8 for Y + 8 for Zr)

## Stage-2 (planned production for H ground-state energetics)
After Stage-1 convergence is accepted, run at converged settings:
- Per system minimum set:
  - host reference (`E_host`)
  - H in tetrahedral site (`E_host+H(T)`)
  - H in octahedral site (`E_host+H(O)`)
- Optional extension:
  - additional symmetry-distinct T/O seeds if relaxation may break symmetry
  - H reference run (commonly H2 molecule setup) for solution-energy reporting consistency

Minimum Stage-2 total planned runs (without symmetry extensions):
- 3 runs/system x 2 systems = 6 production runs (+ optional H reference workflow)

## 3) Step-By-Step Procedure

## A) Prepare Input Files

### A1. Generate/validate config set
From repo root:

```bash
python tools/validate_config.py \
  configs/stage1_y_host_validation_v1.yaml \
  configs/stage1_zr_host_validation_v1.yaml

python tools/plan_stage1_campaign.py \
  --base-config configs/stage1_y_host_validation_v1.yaml \
  --base-config configs/stage1_zr_host_validation_v1.yaml \
  --sweeps both \
  --include-reference \
  --write-json-plan
```

### A2. Patch scheduler placeholders (`partition`, `account`)

```bash
make hpc-patch-scheduler \
  HPC_PARTITION=<your_partition> \
  HPC_ACCOUNT=<your_account> \
  HPC_CONFIG_PATHS="configs/generated/stage1_campaign_<timestamp>"
```

### A3. Initialize run directories

```bash
python tools/hpc/preflight_input_decks.py \
  --init-if-missing \
  --require-potcar true \
  configs/generated/stage1_campaign_<timestamp>
```

### A4. Prepare per-run `inputs/` decks
For each run directory `results/runs/<run_id>/inputs/`, provide:
- `POSCAR`
- `KPOINTS`
- `INCAR`
- `POTCAR`

Important considerations:
- Keep species order consistent between `POSCAR` and `POTCAR`.
- Keep pseudopotential policy consistent across compared cases (`Y_sv`, `Zr_sv`, and H choice for Stage-2).
- For H-site runs, create physically sensible initial H positions (T/O seeds) and avoid unphysical close contacts.
- Use converged Stage-1 settings in Stage-2 to avoid mixing numerical and physical effects.

### A5. Run input preflight gates

```bash
make hpc-preflight-all \
  HPC_CONFIG_PATHS="configs/generated/stage1_campaign_<timestamp>" \
  HPC_REQUIRE_POTCAR=true
```

## B) Set Environment On HPC

### B1. Discover modules and validate VASP install

```bash
tools/hpc/discover_vasp_modules.sh --keyword vasp

tools/hpc/check_vasp_installation.sh \
  --module <compiler_module> \
  --module <mpi_module> \
  --module <vasp_module>
```

Optional smoke execution check:

```bash
tools/hpc/check_vasp_installation.sh \
  --module <compiler_module> \
  --module <mpi_module> \
  --module <vasp_module> \
  --run-smoke true \
  --potcar /path/to/POTCAR \
  --launch-cmd "srun -n 1"
```

### B2. Confirm Python/tooling on frontend node

```bash
pip install -r requirements.txt
make test
```

## C) Execute VASP Runs (Dryrun -> Smoke -> Submit)

### C1. Batch dry-run

```bash
tools/hpc/run_vasp_batch.sh \
  --mode dryrun \
  configs/generated/stage1_campaign_<timestamp>/*.yaml
```

### C2. Batch smoke

```bash
tools/hpc/run_vasp_batch.sh \
  --mode smoke \
  --compiler-module <compiler_module> \
  --mpi-module <mpi_module> \
  --vasp-module <vasp_module> \
  configs/generated/stage1_campaign_<timestamp>/*.yaml
```

### C3. Real batch submit

```bash
tools/hpc/run_vasp_batch.sh \
  --mode submit \
  --continue-on-error true \
  --compiler-module <compiler_module> \
  --mpi-module <mpi_module> \
  --vasp-module <vasp_module> \
  configs/generated/stage1_campaign_<timestamp>/*.yaml
```

## 4) Analyze And Summarize Results

## D) Parse metrics and refresh run reports
After each run completes:

```bash
python tools/extract_metrics.py --run-dir results/runs/<run_id>
python tools/generate_run_report.py --run-dir results/runs/<run_id>
```

Artifacts to inspect:
- `results/runs/<run_id>/metrics.json`
- `results/runs/<run_id>/manifest.json`
- `results/runs/<run_id>/report.html`
- `results/runs/<run_id>/logs/orchestrator/.../pipeline.log`
- `results/runs/<run_id>/logs/slurm/slurm-<jobid>.out|err`

## E) Stage-1 summary expectations
- Plot or tabulate total energy trends vs ENCUT and k-grid for Y and Zr.
- Select a single converged setting policy valid for both systems.
- Record selected settings and rationale in `progress/` and docs.

## F) Stage-2 summary expectations (H in alpha-Y/Zr)
For each system, summarize:
- `E_host`
- `E_host+H(T)`
- `E_host+H(O)`
- Preferred site (lowest total energy after consistent referencing)

Then compare Y vs Zr trends and carry forward to thermodynamic modeling stages.

## 5) Practical Checklist (Short Form)
1. Generate/validate configs.
2. Patch scheduler placeholders.
3. Initialize run directories.
4. Place complete input decks (`POSCAR/KPOINTS/INCAR/POTCAR`).
5. Run `hpc-preflight-all`.
6. Run `dryrun -> smoke -> submit`.
7. Parse metrics and refresh HTML reports.
8. Summarize convergence (Stage-1), then launch H-site production (Stage-2).
