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

## Current Script
- `validate_config.py`: validates stage-1 YAML/JSON configs against `docs/config_schema.md`.
- `init_run.py`: creates run folder structure and starter `manifest.json`/`metrics.json` from config.
- `extract_metrics.py`: parses `raw/OUTCAR` + `raw/OSZICAR` and writes `metrics.json`.
- `presentation/`: deck generation pipeline for major update dissemination (`.pptx` + `.pdf`).
