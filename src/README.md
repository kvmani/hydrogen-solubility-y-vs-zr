# src/

## Purpose
Python package for config resolution, run manifest writing, metrics extraction, and reporting logic.

## Goes In
- Reusable library code only
- Typed models and parsers
- Deterministic reporting utilities

## Does NOT Go In
- Large raw data
- Notebook-only one-off logic

## Mission Link
Implements the reproducibility contracts defined in `docs/data_model.md` and `docs/conventions.md`.

## Status
Baseline implementation in place:
1. stage-1 config loading/validation (`config_models.py`)
2. manifest writing (`pipeline.write_manifest`)
3. metrics writing (`pipeline.write_metrics`)

Future tasks will implement:
1. parser-backed metrics extraction from VASP outputs
2. deterministic HTML report generation
3. stage 2+ schemas and orchestration logic
