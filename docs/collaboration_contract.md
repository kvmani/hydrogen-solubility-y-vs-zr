# Collaboration Contract

This page is the Sphinx-facing summary of the agent and collaborator rules in `agents.md`.

## Purpose

Codex and human collaborators produce reproducible, research-grade outputs in this repository.

## Output Contract

- Update relevant docs first or in the same change set.
- Keep workflows config-driven; avoid hard-coded one-off parameters.
- Emit or update machine-readable provenance artifacts when running computations.
- Report what changed, what was validated, and what remains open.
- For major results or feature additions, generate dissemination artifacts in `presentations/` (`.pptx` and `.pdf`).
- Build-check the docs site when the change touches workflow, science, provenance, or public API surface.

## Documentation-First Rules

- `docs/` is the primary interface; implementation follows documented contracts.
- Any change to run behavior must update:
  - `docs/conventions.md` if naming/layout/provenance changes.
  - `docs/data_model.md` if output JSON structures change.
  - `docs/roadmap.md` if stage gates or sequencing changes.
- Factual scientific claims require primary-source or authoritative citations.
- `docs/index.md` is the Sphinx landing page and canonical navigation hub.
- Scientific-method changes should update `docs/scientific_foundation.md` and, if manuscript-facing, `docs/manuscript_blueprint.md`.

## Collaboration Hygiene

- Do not rewrite history of previous runs; append corrections with new run IDs.
- Keep `progress/` as a living record of decisions, assumptions, and blockers.
- Flag unresolved scientific ambiguity explicitly; do not hide uncertainty.
- Keep presentation manifests and generated decks versioned for traceability.
- Keep the documentation build green for substantive changes.

