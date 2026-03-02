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

Required subpaths/files (baseline contract):
- `inputs/` snapshot of INCAR/KPOINTS/POSCAR/POTCAR metadata and config
- `logs/` scheduler + code logs
- `raw/` parser-ready raw outputs
- `parsed/` extracted tables/json
- `manifest.json`
- `metrics.json`
- `report.html` (required in later tasks)

## Config Convention
- Store config files in `configs/`.
- Use explicit, versioned names, e.g., `stage2_y_dilute_h_v1.yaml`.
- No hidden defaults without docs mention.

## Metadata And Provenance Expectations
`manifest.json` must include:
- run ID, UTC timestamp, git commit hash
- host/system identity and structure source
- pseudopotential identifiers and exchange-correlation functional
- convergence settings and scheduler metadata
- software versions (VASP, parser tools, Python package)

`metrics.json` must include:
- key converged energies and derived quantities
- pass/fail for predefined checks
- links to source files in the run directory

## Documentation Synchronization Rule
Any change to conventions here requires corresponding updates in:
- `docs/data_model.md` for schema impacts
- `agents.md` if process rules change
