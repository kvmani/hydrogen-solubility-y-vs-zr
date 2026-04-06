# Provenance And Contract

This project treats each run as a traceable scientific object, not as a loose collection of files.

## Run Identity

Every run has a unique `run_id` with the form:

`YYYYMMDD_<system>_<stage>_<method>_<seq>`

That identifier determines the result folder:

`results/runs/<run_id>/`

The run directory is the unit of provenance, parsing, reporting, and future comparison.

## Required Artifacts

Each run must carry the following baseline artifacts:

- `inputs/config_snapshot.yaml` or `.json`
- `manifest.json`
- `metrics.json`
- `report.html`
- `logs/`
- `raw/`
- `parsed/`

When the run reaches the HPC layer, the manifest must also record execution events and submission metadata.

## Manifest Semantics

`manifest.json` is the provenance record.

It captures:

- run identity,
- UTC timestamp,
- stage and system,
- code version metadata,
- Git commit and dirty-state status,
- input configuration paths and key VASP settings,
- scheduler settings,
- result paths,
- execution events.

The execution events list is important. It records the operational history of the run, including dry-run, smoke, and submit attempts. That makes the run auditable long after the workflow completed.

## Metrics Semantics

`metrics.json` is the numerical record.

It captures:

- total energies,
- energy-per-atom values,
- derived formation or solution energies when available,
- convergence checks,
- artifact paths,
- a status flag such as `initialized`, `success`, `partial`, or `failed`.

This file should remain machine-readable and schema-stable. When the schema changes, the documentation contract must change with it.

## Human Report Semantics

`report.html` is a human QA surface.

It should answer four questions quickly:

1. What was this run trying to do?
2. Which inputs governed it?
3. What did the parser recover?
4. Is the run usable for the next stage?

That is why the report is regenerated whenever `manifest.json` or `metrics.json` changes.

## Change Matrix

When a change lands, update the corresponding docs in the same change set.

| Change type | Required documentation |
| --- | --- |
| New or changed config field | `docs/config_schema.md`, `docs/conventions.md` |
| New output JSON field | `docs/data_model.md` |
| New stage gate or workflow step | `docs/roadmap.md`, `docs/computational_workflow.md` |
| New parser behavior | `docs/computational_workflow.md`, `docs/api_reference.md` |
| New scientific claim or interpretation | `docs/scientific_foundation.md`, `literature/lit_review.md` |
| New manuscript-facing narrative | `docs/manuscript_blueprint.md` |

## Repository-Wide Rule

The documentation site under `docs/` is the canonical human interface for the project.

Any substantive development task should leave the docs in a better state than before it started. That means:

- no undocumented change in algorithm or data contract,
- no uncited scientific claim,
- no run-behavior change without a docs update,
- no merge without a successful docs build.
