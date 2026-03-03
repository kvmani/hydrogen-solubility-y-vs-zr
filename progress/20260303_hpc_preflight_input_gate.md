# 2026-03-03: HPC Input-Deck Preflight Gate Added

## What Changed
- Added `tools/hpc/preflight_input_decks.py` to audit required files under `results/runs/<run_id>/inputs` for config sets.
- Required-file gate supports:
  - `INCAR`, `POSCAR`, `KPOINTS` always
  - optional `POTCAR` via `--require-potcar true|false`
  - `--fail-if-unready` for CI/Make gating
  - optional `--init-if-missing` to bootstrap run directories before checks
- Added Make targets:
  - `hpc-preflight-inputs`
  - `hpc-preflight-all` (scheduler + input checks)
- Updated HPC onboarding and campaign docs with preflight-input gate before batch launch.

## Validation
- `python -m compileall src tools` passed.
- `make test` passed.
- `preflight_input_decks.py --help` reviewed.
- Dry checks over base and campaign configs report missing deck files as expected.
- `--init-if-missing` path verified using temporary `--results-root`.

## Current Blockers
- Scheduler placeholders remain in several configs (`<partition>`, `<account>`).
- Input decks are incomplete for many runs (missing at least `POSCAR`, `KPOINTS`, `POTCAR` in current local state).

## Next Actions
1. Patch scheduler placeholders with site values.
2. Stage complete input decks in each run `inputs/` directory.
3. Run `make hpc-preflight-all` until clean before smoke/submit.
