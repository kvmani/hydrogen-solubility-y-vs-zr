# tools/

## Purpose
CLI-facing helper scripts for repeatable project operations.

## Goes In
- Small automation utilities (e.g., parsing, report assembly, consistency checks)
- Script wrappers that consume config files and emit standardized outputs

## Does NOT Go In
- Core reusable logic (belongs in `src/`)
- Environment-specific hacks without documentation

## Mission Link
Supports reproducible execution while keeping orchestration explicit and reviewable.

## Current Scripts
- `validate_config.py`: validates stage-1 YAML/JSON configs against `docs/config_schema.md`.
- `init_run.py`: creates run folder structure and starter `manifest.json`/`metrics.json` from config.
- `extract_metrics.py`: parses `raw/OUTCAR` + `raw/OSZICAR` and writes `metrics.json`.
- `plan_stage1_campaign.py`: generates Stage-1 convergence campaign config sets and plan tables.
- `presentation/`: deck generation pipeline for major update dissemination (`.pptx` + `.pdf`).
- `hpc/discover_vasp_modules.sh`: discovers candidate VASP modules and resolved binaries on your HPC.
- `hpc/check_vasp_installation.sh`: quick + smoke checks for VASP availability and execution health.
- `hpc/run_vasp_pipeline.sh`: single-run dryrun/smoke/submit orchestrator.
- `hpc/run_vasp_batch.sh`: batch launcher for multiple configs.
- `hpc/submit_vasp_job.sh`: Slurm submit wrapper preserving submit provenance.
- `hpc/update_manifest_event.py`: appends execution events and submission metadata to `manifest.json`.
