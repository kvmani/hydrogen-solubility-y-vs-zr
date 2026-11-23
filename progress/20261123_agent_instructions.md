# 2026-11-23: Agent instructions refactor

## Why

The owner standardised agent instructions across all repositories: one `AGENTS.md` read by every
coding agent (Codex, Claude, Gemini), with common cardinal rules — fetch before changing, work on
`main`, keep the progress ledger current, run targeted tests for ordinary changes, and run CI
only on request.

## Decisions

- `agents.md` renamed to `AGENTS.md` (the name agents look for on case-sensitive systems);
  `docs/collaboration_contract.md` and `README.md` now point to the new name.
- Every existing rule is kept verbatim (config-driven physics, docs-update table, reproducibility,
  scientific hygiene). "Run `make check` before merging" became "run the checks for what you
  changed; `make check` before a release" per the owner's rule on test scope; the Makefile help
  text says the same.
- `.github/workflows/ci.yml` now runs only by hand (`workflow_dispatch`); it previously ran on
  every push to `main` and on pull requests.
- `progress/` is the progress ledger; `.gemini/settings.json` points Gemini CLI at `AGENTS.md`.

## Evidence

- `python -m sphinx -W -q -b html docs <out>` passed before and after the change (the contract
  page includes `AGENTS.md`, which is kept free of relative links for that reason).

## Next actions

None for this task.
