# Config Schema (Stage 1 Baseline)

This document defines the first enforced config contract for host-only Stage-1 runs.

## Scope
- Supported today: `stage1` host validation configs for `Y` and `Zr`.
- File formats: `.yaml`, `.yml`, `.json`.
- Schema version: `1.0`.

## Validator Entry Point
- CLI: `python tools/validate_config.py <config-path> [<config-path> ...]`
- Python API: `hydrogen_solubility.load_stage1_host_config(path)`

## Required Top-Level Keys
- `schema_version`
- `run`
- `structure`
- `vasp`
- `convergence_scan`
- `hpc`
- `outputs`
- `provenance`

## Key Constraints
- `run.run_id` format:
  - `YYYYMMDD_<system>_<stage>_<method>_<seq>`
  - Example: `20260302_Y_stage1_dft_001`
- `run.stage` must be `stage1`.
- `run.system` must match run ID (`Y` or `Zr`).
- `run.method` must match run ID and currently must be `dft`.
- `vasp.encut_eV` must appear in `convergence_scan.encut_values_eV`.
- `vasp.kpoints_grid` must appear in `convergence_scan.kpoint_grids`.
- `hpc.walltime` must match `HH:MM:SS`.
- `provenance.potcar_labels` must include system-appropriate label:
  - `Y*` for `system=Y`
  - `Zr*` for `system=Zr`

## Starter Configs
- `configs/stage1_y_host_validation_v1.yaml`
- `configs/stage1_zr_host_validation_v1.yaml`

Use these as templates; do not mutate in-place for new variants. Create a new versioned config file per meaningful change.
