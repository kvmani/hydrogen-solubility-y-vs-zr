# API Reference

The Python package is intentionally small. The API reference documents the exact functions and classes that underpin the workflow contract.

## Package Overview

```{automodule} hydrogen_solubility
:members:
:undoc-members:
:show-inheritance:
```

## Configuration Models

```{automodule} hydrogen_solubility.config_models
:members:
:undoc-members:
:show-inheritance:
```

## Workflow Pipeline

```{automodule} hydrogen_solubility.pipeline
:members:
:undoc-members:
:show-inheritance:
```

## Run Bootstrap

```{automodule} hydrogen_solubility.run_bootstrap
:members:
:undoc-members:
:show-inheritance:
```

## VASP Metrics Parsing

```{automodule} hydrogen_solubility.vasp_metrics
:members:
:undoc-members:
:show-inheritance:
```

## Reporting Utilities

```{automodule} hydrogen_solubility.reporting
:members:
:undoc-members:
:show-inheritance:
```

## Command-Line Entry Points

- `python tools/validate_config.py <config-path>`
- `python tools/init_run.py <config-path>`
- `python tools/extract_metrics.py --run-dir results/runs/<run_id>`
- `python tools/generate_run_report.py --run-dir results/runs/<run_id>`
- `python tools/plan_stage1_campaign.py --base-config ...`
- `tools/hpc/run_vasp_pipeline.sh --mode dryrun|smoke|submit --config <config>`

These scripts are thin wrappers around the package modules above. The thin-wrapper pattern keeps orchestration explicit and makes the reusable logic importable in tests or future notebooks.
