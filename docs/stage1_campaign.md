# Stage-1 Convergence Campaign (Y + Zr)

This guide operationalizes Stage-1 (host-only validation) using generated config families and dry-run-first orchestration.

## Goal
Produce a reproducible ENCUT and k-point convergence dataset for alpha-Y and alpha-Zr before any Stage-2 H-interstitial calculations.

## 1) Generate Campaign Configs
Generate sweep configs from baseline templates:

```bash
python tools/plan_stage1_campaign.py \
  --base-config configs/stage1_y_host_validation_v1.yaml \
  --base-config configs/stage1_zr_host_validation_v1.yaml \
  --sweeps both \
  --include-reference \
  --write-json-plan
```

Outputs:
- `configs/generated/stage1_campaign_<timestamp>/` (YAML configs)
- `stage1_campaign_plan.csv` (execution order + metadata)
- optional `stage1_campaign_plan.json`

## 2) Preflight + Validate Generated Configs
Audit scheduler readiness (partition/account placeholders) and schema validity:

```bash
python tools/hpc/preflight_scheduler_configs.py \
  --fail-if-unready \
  configs/generated/stage1_campaign_<timestamp>
```

If placeholders remain, patch them in-place:

```bash
python tools/hpc/preflight_scheduler_configs.py \
  --set-partition <partition> \
  --set-account <account> \
  --write \
  configs/generated/stage1_campaign_<timestamp>
```

Then run schema validation:

```bash
python tools/validate_config.py configs/generated/stage1_campaign_<timestamp>/*.yaml
```

## 3) Preflight Input Deck Completeness
After run directories are initialized and input decks are staged in each `inputs/` folder:

```bash
python tools/hpc/preflight_input_decks.py \
  --require-potcar true \
  --fail-if-unready \
  configs/generated/stage1_campaign_<timestamp>
```

Optional bootstrap for missing run directories (still requires manual deck placement):

```bash
python tools/hpc/preflight_input_decks.py \
  --require-potcar true \
  --init-if-missing \
  configs/generated/stage1_campaign_<timestamp>
```

## 4) Frontend Dry-Run First
Run dry-run over all generated configs:

```bash
tools/hpc/run_vasp_batch.sh \
  --mode dryrun \
  configs/generated/stage1_campaign_<timestamp>/*.yaml
```

Dry-run checks config validity, run directory state, input readiness, and rendered sbatch syntax.

## 5) Frontend Smoke Checks
After filling required `inputs/` decks (`POSCAR`, `KPOINTS`, `INCAR`, and `POTCAR` for submit mode):

```bash
tools/hpc/run_vasp_batch.sh \
  --mode smoke \
  --compiler-module <compiler_module> \
  --mpi-module <mpi_module> \
  --vasp-module <vasp_module> \
  configs/generated/stage1_campaign_<timestamp>/*.yaml
```

## 6) Submit Real Jobs
Only after dry-run and smoke pass:

```bash
tools/hpc/run_vasp_batch.sh \
  --mode submit \
  --continue-on-error true \
  --compiler-module <compiler_module> \
  --mpi-module <mpi_module> \
  --vasp-module <vasp_module> \
  configs/generated/stage1_campaign_<timestamp>/*.yaml
```

## 7) Parse Results
After each run finishes:

```bash
python tools/extract_metrics.py --run-dir results/runs/<run_id>
```

## 8) Stage-1 Exit Criteria
- ENCUT convergence achieved for Y and Zr at target tolerance (`convergence_scan.tolerance_meV_per_atom`).
- k-point convergence achieved for Y and Zr with consistent methodology.
- All accepted runs have `manifest.json`, `metrics.json`, and traceable logs.
