# Mission

This page is the Sphinx-facing summary of the project mission described in `mission_goals.md`.

## Scientific Vision

Build a mechanistically explicit and quantitatively testable explanation of the hydrogen solubility contrast between yttrium and zirconium, grounded in first-principles energetics and finite-temperature thermodynamics.

## Core Question

Why does hydrogen exhibit substantially higher solubility in Y than in Zr under comparable conditions, despite both being early transition metals with strong hydrogen affinity trends?

## Scope

- In scope:
  - H in dilute interstitial sites of hcp alpha-Y and hcp alpha-Zr.
  - DFT-derived solution energetics, site preference, and migration-relevant energetics.
  - Vibrational/ZPE corrections and thermodynamic mapping to concentration-vs-temperature behavior.
  - Competition with hydride phases where thermodynamically required.
- Out of scope for the baseline project:
  - Defect-rich irradiation microstructure coupling.
  - Mechanical fracture modeling beyond thermodynamic/energetic relevance.
  - Cluster-specific workflow hard-coding.

## Deliverables

- Reproducible input decks, configs, manifests, and metrics for each run stage.
- Dry-run, smoke-test, and submission logs with root-cause-friendly diagnostics.
- Literature-backed quantitative model for H solubility contrast in Y vs Zr.
- Comparison plots against experimental/assessed data.
- Manuscript-ready figures, tables, and a methods-complete narrative.

## Non-Negotiables

- No uncited factual claims in mission/docs/literature outputs.
- No one-off manual runs counted as evidence without machine-readable provenance.
- No result acceptance without convergence checks and stage-gate criteria.
- Documentation and code/results must stay synchronized in every substantive task.
- Slurm workflows must pass frontend `dryrun` and `smoke` checks before real submission.

