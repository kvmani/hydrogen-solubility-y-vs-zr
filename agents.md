# Agent And Collaborator Contract

Rules for humans and coding agents working in this repository.

## Every substantive change

- Keep work config-driven: physics lives in `configs/campaigns/`, cluster settings in
  `configs/site.yaml`; code contains no hidden scientific defaults.
- Update the matching docs in the same change set (table below) and run `make check`
  (lint, tests, docs build) before merging.
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
