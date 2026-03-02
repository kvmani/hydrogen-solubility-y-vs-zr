# Agent And Collaborator Contract

## Purpose
Define how Codex and human collaborators produce reproducible, research-grade outputs in this repository.

## Output Contract (Every Substantive Task)
- Update relevant docs first or in the same change set.
- Keep workflows config-driven; avoid hard-coded one-off parameters.
- Emit or update machine-readable provenance artifacts when running computations.
- Report what changed, what was validated, and what remains open.

## Documentation-First Rules
- `docs/` is the primary interface; implementation follows documented contracts.
- Any change to run behavior must update:
  - `docs/conventions.md` if naming/layout/provenance changes.
  - `docs/data_model.md` if output JSON structures change.
  - `docs/roadmap.md` if stage gates or sequencing changes.
- Factual scientific claims require primary-source or authoritative citations.

## Reproducibility Expectations
- Every run gets a unique `run_id` and dedicated results folder.
- Required per-run artifacts:
  - input snapshot
  - `manifest.json`
  - `metrics.json`
  - logs
- Future tasks must also produce an HTML run report for human inspection.

## Config-Driven Workflow Policy
- All operational settings must come from `configs/` files (or explicit defaults documented in code/docs).
- Scripts in `tools/` and package code in `src/` must accept config paths/IDs, not embedded constants.
- Config changes should be reviewable diffs and traceable to run IDs.

## Collaboration Hygiene
- Do not rewrite history of previous runs; append corrections with new run IDs.
- Keep `progress/` as a living record of decisions, assumptions, and blockers.
- Flag unresolved scientific ambiguity explicitly; do not hide uncertainty.
