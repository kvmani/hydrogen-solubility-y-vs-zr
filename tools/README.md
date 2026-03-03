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
- `init_run.py`: creates run folder structure and starter `manifest.json`/`metrics.json`/`report.html` from config.
- `extract_metrics.py`: parses `raw/OUTCAR` + `raw/OSZICAR`, writes `metrics.json`, and refreshes `report.html`.
- `generate_run_report.py`: regenerates `report.html` from existing run JSON artifacts.
- `plan_stage1_campaign.py`: generates Stage-1 convergence campaign config sets and plan tables.
- `presentation/`: deck generation pipeline for major update dissemination (`.pptx` + `.pdf`).
- `hpc/discover_vasp_modules.sh`: discovers candidate VASP modules and resolved binaries on your HPC.
- `hpc/check_vasp_installation.sh`: quick + smoke checks for VASP availability and execution health.
- `hpc/preflight_scheduler_configs.py`: audits and optionally patches `hpc.partition`/`hpc.account` placeholders in config files.
- `hpc/preflight_input_decks.py`: audits required run input files under `results/runs/<run_id>/inputs` for config sets.
- `hpc/run_vasp_pipeline.sh`: single-run dryrun/smoke/submit orchestrator.
- `hpc/run_vasp_batch.sh`: batch launcher for multiple configs.
- `hpc/submit_vasp_job.sh`: Slurm submit wrapper preserving submit provenance.
- `hpc/update_manifest_event.py`: appends execution events and submission metadata to `manifest.json`.
