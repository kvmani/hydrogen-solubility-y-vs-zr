# Conventions

## Run ID Convention
Use:
`YYYYMMDD_<system>_<stage>_<method>_<seq>`

Example:
`20260302_Y_stage2_dft_001`

Field rules:
- `system`: `Y`, `Zr`, `YH_x`, `ZrH_x`, or explicit alloy tag.
- `stage`: `stage1` ... `stage6` aligned to `docs/roadmap.md`.
- `method`: short tag (`dft`, `phonon`, `thermo`, `post`).
- `seq`: zero-padded integer for retries/variants.

## Folder Convention (Per Run)
Each run lives at:
`results/runs/<run_id>/`

Bootstrap command:
`python tools/init_run.py <config-file>`

Required subpaths/files (baseline contract):
- `inputs/` snapshot of INCAR/KPOINTS/POSCAR/POTCAR metadata and config
- `logs/` scheduler + orchestration + parser logs
- `raw/` parser-ready raw outputs
- `parsed/` extracted tables/json
- `manifest.json`
- `metrics.json`
- `report.html` (required in later tasks)

Metrics parser command:
`python tools/extract_metrics.py --run-dir results/runs/<run_id>`

## HPC Pipeline Convention
Required execution order before real scheduler submission:
1. `dryrun`
2. `smoke`
3. `submit`

Reference scripts:
- Single config: `tools/hpc/run_vasp_pipeline.sh`
- Batch configs: `tools/hpc/run_vasp_batch.sh`

Orchestrator session logs:
- `results/runs/<run_id>/logs/orchestrator/<timestamp>_<mode>/pipeline.log`

Rendered sbatch scripts:
- `results/runs/<run_id>/logs/slurm/<run_id>_<timestamp>.sbatch`

## Config Convention
- Store config files in `configs/`.
- Use explicit, versioned names, e.g., `stage2_y_dilute_h_v1.yaml`.
- No hidden defaults without docs mention.
- Validate every config against `docs/config_schema.md` before submission.

## Literature Benchmark Convention
- Store extracted benchmark data under `literature/benchmarks/`.
- Use CSV as canonical machine-readable format for target curves/anchors.
- Every benchmark row must include DOI, source location, and extraction status.

## Presentation Convention
- Major update deck naming:
  - `<YYYYMMDD>_<stage_or_feature>_<topic>.pptx`
  - `<YYYYMMDD>_<stage_or_feature>_<topic>.pdf`
- Keep the generated manifest next to decks:
  - `<YYYYMMDD>_<stage_or_feature>_<topic>_manifest.json`

## Metadata And Provenance Expectations
`manifest.json` must include:
- run ID, UTC timestamp, git commit hash
- host/system identity and structure source
- pseudopotential identifiers and exchange-correlation functional
- convergence settings and scheduler metadata
- software versions (VASP, parser tools, Python package)
- execution events for dryrun/smoke/submit attempts

`metrics.json` must include:
- key converged energies and derived quantities
- pass/fail for predefined checks
- links to source files in the run directory

## Documentation Synchronization Rule
Any change to conventions here requires corresponding updates in:
- `docs/data_model.md` for schema impacts
- `agents.md` if process rules change
