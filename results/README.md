# results/

## Purpose
Store all computational outputs in a strict, run-ID-indexed structure.

## Goes In
- `runs/<run_id>/` directories with inputs, raw outputs, parsed summaries, and required JSON artifacts
- Aggregate derived tables/plots in dedicated subfolders

## Does NOT Go In
- Source code
- Unnamed or untracked scratch output

## Mission Link
Provides auditable evidence trails linking conclusions to exact computational artifacts.

## Required Layout (per run)
`results/runs/<run_id>/`
- `inputs/`
- `logs/`
- `raw/`
- `parsed/`
- `manifest.json`
- `metrics.json`
- `report.html` (required in later tasks)
