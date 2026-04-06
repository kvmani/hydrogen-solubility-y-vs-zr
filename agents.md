# Agent And Collaborator Contract

## Purpose
Define how Codex and human collaborators produce reproducible, research-grade outputs in this repository.

## Output Contract (Every Substantive Task)
- Update relevant docs first or in the same change set.
- Keep workflows config-driven; avoid hard-coded one-off parameters.
- Emit or update machine-readable provenance artifacts when running computations.
- Report what changed, what was validated, and what remains open.
 - For major results or feature additions, generate dissemination artifacts in `presentations/` (`.pptx` and `.pdf`) for review, but do not commit the generated binaries.
- Build-check the docs site when the change touches workflow, science, provenance, or public API surface.

## Documentation-First Rules
- `docs/` is the primary interface; implementation follows documented contracts.
- Any change to run behavior must update:
  - `docs/conventions.md` if naming/layout/provenance changes.
  - `docs/data_model.md` if output JSON structures change.
  - `docs/roadmap.md` if stage gates or sequencing changes.
- Factual scientific claims require primary-source or authoritative citations.
- `docs/index.md` is the Sphinx landing page and the canonical navigation hub.
- Scientific-method changes should update `docs/scientific_foundation.md` and, if manuscript-facing, `docs/manuscript_blueprint.md`.
- Algorithm or parser changes should update `docs/computational_workflow.md` and `docs/api_reference.md` if the exported surface changes.
- New claims and reference anchors should be added to `literature/lit_review.md` and `literature/library.bib` in the same change set.

## Reproducibility Expectations
- Every run gets a unique `run_id` and dedicated results folder.
- Required per-run artifacts:
  - input snapshot
  - `manifest.json`
  - `metrics.json`
  - logs
- Frontend `dryrun` and `smoke` checks are mandatory before `submit` mode.
- Workflow execution should use `tools/hpc/run_vasp_pipeline.sh` (single) or `tools/hpc/run_vasp_batch.sh` (batch) unless a documented exception is approved.
- Every pipeline invocation must append an event to `manifest.json` (`execution_events`) and store session logs under `results/runs/<run_id>/logs/orchestrator/`.
- Future tasks must also produce an HTML run report for human inspection.
- Major milestone reports should include a slide deck pair in `presentations/` for inspection, but the generated `.pptx` and `.pdf` files are treated as build artifacts and left untracked.

## Config-Driven Workflow Policy
- All operational settings must come from `configs/` files (or explicit defaults documented in code/docs).
- Scripts in `tools/` and package code in `src/` must accept config paths/IDs, not embedded constants.
- Config changes should be reviewable diffs and traceable to run IDs.

## Collaboration Hygiene
- Do not rewrite history of previous runs; append corrections with new run IDs.
- Keep `progress/` as a living record of decisions, assumptions, and blockers.
- Flag unresolved scientific ambiguity explicitly; do not hide uncertainty.
- Keep presentation source notes and deck generation inputs reproducible; do not rely on committing generated slide binaries for traceability.
- Keep the documentation build green. If a change affects scientific reasoning or workflow semantics, update the docs before closing the task.
