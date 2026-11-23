# AGENTS.md — Hydrogen solubility in Y vs Zr (DFT)

Rules for humans and coding agents (Codex, Claude, Gemini, …) working in this repository: a
config-driven DFT (VASP on Slurm) campaign comparing hydrogen solubility in yttrium and
zirconium, driven by the `./hsol` CLI. This is the only agent-instruction file in the repository;
it is also published in the documentation as the collaboration contract.

**Order of authority:** the owner's instruction for the task → this file → `docs/mission.md` and
`mission_goals.md` → `docs/scheme.md` and `docs/scientific_foundation.md` → `docs/workflow.md`.

## Cardinal rules (owner-mandated, every repository)

1. **Fetch before you change anything.** Start every task with
   `git fetch origin && git pull --rebase --autostash origin main`. Several people and agents push
   to this repository; never build on a stale checkout.
2. **Work on `main` only.** Commit and push directly to `main` unless the owner names another
   branch for the task. No feature branches or pull requests by default. Fetch again before
   pushing; if the push is rejected, `git pull --rebase origin main`, rerun the affected tests,
   then push. Never force-push or rewrite published history.
3. **Keep the progress ledger current:** `progress/`. Before coding, add (or claim)
   the task entry: goal, plan, who is working on it, date. After each meaningful step record what
   was done, the commit, test evidence, decisions, blockers and the next step. Commit the ledger
   with the work it describes. A new session must be able to resume from the ledger and git
   history alone, without the chat that started the work.
4. **Targeted tests for ordinary changes.** Run only the tests that cover what you touched (see
   "Tests"). Run the full suite only when preparing a release or when the owner asks.
5. **CI runs only on request.** GitHub Actions workflows start by `workflow_dispatch` only;
   tag-triggered release workflows are the single exception. Never add push, pull-request or
   schedule triggers, and never start a workflow unless the owner asks.
6. **Be honest.** Never report a check as passed unless you ran it and saw it pass; record skipped
   checks and the reason. Never weaken, skip or delete a test to make it pass.
7. **Keep git clean.** Commit sources and canonical assets only: no secrets, real personal data,
   virtual environments, caches, logs or build output.

The cardinal rules decide *how work is done* (sync, branch, ledger, test scope, CI). The project
rules in this file decide *what this repository must achieve and protect*; nothing generic here
relaxes them. If a project rule and a cardinal rule genuinely conflict, stop and ask the owner.

## Every substantive change

- Keep work config-driven: physics lives in `configs/campaigns/`, cluster settings in
  `configs/site.yaml`; code contains no hidden scientific defaults.
- Update the matching docs in the same change set (table below) and run the checks for what you
  changed (see Tests); run `make check` (lint, tests, docs build) before a release or when asked.
- Report what changed, what was validated, and what remains open; record decisions in `progress/`.
- Major results get a lab-meeting deck via `tools/presentation/`; generated decks are not committed.

| If you change… | also update |
|---|---|
| a campaign/config key or schema | `docs/config_schema.md` |
| run layout, manifest or metrics fields | `docs/data_model.md` |
| commands or their order | `docs/workflow.md`, `README.md` |
| equations, assumptions, interpretation | `docs/scheme.md`, `docs/scientific_foundation.md` |
| stage gates or priorities | `docs/roadmap.md` |
| a scientific claim or reference | `literature/lit_review.md`, `literature/library.bib` |

## Reproducibility

- Every calculation is a run with a unique id and directory created by `hsol prepare`; one-off
  manual VASP runs do not count as evidence.
- Slurm work goes through `hsol run` in the order `dryrun → smoke → submit` (enforced).
- Never overwrite a run: changed physics gets a new id via the campaign `tag`.
- Never edit generated files (`configs/generated/`, `results/runs/*/inputs/`) by hand.
- Never commit POTCAR files or `configs/site.yaml`.

## Scientific hygiene

- Factual claims need primary-source or authoritative citations (DOI) in `literature/library.bib`.
- Only `converged` runs feed analyses; state uncertainty and model assumptions explicitly.
- Y and Zr are always computed with identical settings (`common_settings.yaml`,
  `converged_settings.yaml`).

## Quality bar

- The smallest change that fully solves the task; no dead code; physics only from campaign files.
- Type hints and docstrings on every public function, stating units and the equation or source
  it implements; validate configs through the schema in `config_models.py` and fail with an
  actionable message.
- Every behaviour change ships with a test in the same commit; numerical code is tested against
  hand-checked values with explicit tolerances.
- `ruff check` and `ruff format --check` clean on touched files.

## How to work

1. Sync (cardinal rule 1); read the latest notes in `progress/` and `docs/roadmap.md`.
2. Read only the docs from the table above that match the task, then the code and its tests.
3. Start or update a dated note in `progress/` (goal, plan, decisions, evidence, next action);
   implement in small verified steps; commit, push and update the note after each.

## Tests

```bash
python -m pip install -r requirements-dev.txt -r requirements-docs.txt
python -m pytest tests/test_<area>.py -q      # targeted (ordinary changes)
make lint                                     # touched Python or HPC shell scripts
make docs                                     # any change under docs/ or to this file
make check                                    # lint + all tests + docs (release or on request)
```

| You changed | Run |
| --- | --- |
| `config_models.py`, `planner.py`, campaign or site configs | `tests/test_config_and_planner.py` |
| `structures.py` | `tests/test_structures.py` |
| `thermo.py`, `solubility.py` | `tests/test_thermo.py` |
| `vasp_metrics.py`, `convergence.py` | `tests/test_vasp_metrics.py` |
| `pipeline.py`, `cli.py`, `run_bootstrap.py`, `vasp_inputs.py`, `./hsol` | `tests/test_workflow.py` |

## Definition of done

- [ ] Targeted checks pass and were run; docs from the table updated in the same change set.
- [ ] No hidden scientific defaults; no POTCAR, `configs/site.yaml` or generated files committed.
- [ ] Decision and evidence recorded in `progress/`; committed and pushed to `main`.
