# configs/

## Purpose
Store versioned, reviewable run configurations that drive all workflows.

## Goes In
- YAML/JSON config files per stage/system
- Explicit parameter sets and references to template inputs
- Versioned config variants (do not overwrite old experiment definitions)

## Does NOT Go In
- Binary outputs or generated logs
- Undocumented ad hoc parameter overrides

## Mission Link
Config-driven execution ensures reproducibility and fair Y-vs-Zr comparisons.

## Validation
- Schema reference: `docs/config_schema.md`
- Validate configs before running:
  - `python tools/validate_config.py configs/stage1_y_host_validation_v1.yaml`
  - `python tools/validate_config.py configs/stage1_zr_host_validation_v1.yaml`
