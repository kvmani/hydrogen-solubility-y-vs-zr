# First-principles explanation of hydrogen solubility contrast in Y vs Zr

Documentation-first, reproducible research scaffold for building a quantitatively defensible DFT + thermodynamics explanation of why hydrogen solubility is much higher in yttrium than in zirconium.

## Start Here
- Mission and scientific scope: `mission_goals.md`
- Collaboration contract for Codex/humans: `agents.md`
- Execution plan and stage gates: `docs/roadmap.md`
- Local/HPC bootstrap: `docs/getting_started.md`
- Literature map and bibliography: `literature/lit_review.md`, `literature/library.bib`
- Machine-readable literature benchmarks: `literature/benchmarks/`

## Repository Layout
- `docs/`: roadmap, conventions, data contracts, onboarding
- `literature/`: curated references, BibTeX, evidence map
- `hpc/`: VASP/SLURM templates and runbook
- `configs/`: run-time configuration files (YAML/JSON)
- `src/`: analysis package (placeholder)
- `tools/`: utility scripts (placeholder)
- `results/`: run artifacts under strict run-ID layout
- `presentations/`: slide decks and figures for reporting
- `progress/`: living logs and decision records

## Reproducibility Principles
- Every computational run must be config-driven and emit `manifest.json` + `metrics.json`.
- Factual claims in docs must cite primary sources (DOI or authoritative handbook).
- Human-readable run reports (HTML) are required for each completed run in later tasks.
- Major updates must also generate dissemination decks (`.pptx` + `.pdf`) in `presentations/`.

## Quick Commands
- Validate configs: `python tools/validate_config.py configs/stage1_y_host_validation_v1.yaml configs/stage1_zr_host_validation_v1.yaml`
- Initialize run folders/artifacts: `python tools/init_run.py configs/stage1_y_host_validation_v1.yaml`
- Generate update deck: `python tools/presentation/generate_lab_meeting_ppt.py --scan-root results --output-dir presentations --deck-title "Y vs Zr Update" --require-pdf`
