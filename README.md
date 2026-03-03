# First-principles explanation of hydrogen solubility contrast in Y vs Zr

Documentation-first, reproducible research scaffold for building a quantitatively defensible DFT + thermodynamics explanation of why hydrogen solubility is much higher in yttrium than in zirconium.

## Start Here
- Mission and scientific scope: `mission_goals.md`
- Collaboration contract for Codex/humans: `agents.md`
- Execution plan and stage gates: `docs/roadmap.md`
- VASP primer (concepts + workflow): `docs/vasp_primer.md`
- End-to-end VASP execution guide (inputs + HPC + analysis): `docs/vasp_simulation_guide.md`
- Local/HPC bootstrap: `docs/getting_started.md`
- Stage-1 campaign guide: `docs/stage1_campaign.md`
- Beginner VASP tutorial: `hpc/beginner_vasp_tutorial.md`
- Module discovery tutorial: `hpc/vasp_module_discovery_tutorial.md`
- Slurm/VASP operator tutorial: `hpc/runbook.md`
- Literature map and bibliography: `literature/lit_review.md`, `literature/library.bib`
- Machine-readable literature benchmarks: `literature/benchmarks/`

## Repository Layout
- `docs/`: roadmap, conventions, data contracts, onboarding
- `literature/`: curated references, BibTeX, evidence map
- `hpc/`: VASP/SLURM templates and runbook
- `configs/`: run-time configuration files (YAML/JSON)
- `src/`: analysis package
- `tools/`: CLI utilities and orchestration scripts
- `results/`: run artifacts under strict run-ID layout
- `presentations/`: slide decks and figures for reporting
- `progress/`: living logs and decision records

## Reproducibility Principles
- Every computational run must be config-driven and emit `manifest.json` + `metrics.json`.
- Every computational run should also emit/update `report.html` for fast human QA.
- Slurm execution must follow `dryrun -> smoke -> submit`.
- Factual claims in docs must cite primary sources (DOI or authoritative handbook).
- Human-readable run reports (HTML) are required for each completed run in later tasks.
- Major updates must also generate dissemination decks (`.pptx` + `.pdf`) in `presentations/`.

## Quick Commands
- Validate configs:
  - `python tools/validate_config.py configs/stage1_y_host_validation_v1.yaml configs/stage1_zr_host_validation_v1.yaml`
- Preflight scheduler readiness (placeholders/validation):
  - `python tools/hpc/preflight_scheduler_configs.py --fail-if-unready configs/stage1_y_host_validation_v1.yaml configs/stage1_zr_host_validation_v1.yaml`
- Patch scheduler placeholders in bulk:
  - `python tools/hpc/preflight_scheduler_configs.py --set-partition <partition> --set-account <account> --write configs/stage1_y_host_validation_v1.yaml configs/stage1_zr_host_validation_v1.yaml`
  - `make hpc-patch-scheduler HPC_PARTITION=<partition> HPC_ACCOUNT=<account>`
- Preflight run input decks before batch launch:
  - `python tools/hpc/preflight_input_decks.py --require-potcar true --fail-if-unready configs/stage1_y_host_validation_v1.yaml configs/stage1_zr_host_validation_v1.yaml`
  - `make hpc-preflight-inputs`
- Run combined preflight gates:
  - `make hpc-preflight-all`
- Generate Stage-1 convergence campaign:
  - `make plan-stage1`
- Initialize run folders/artifacts:
  - `python tools/init_run.py configs/stage1_y_host_validation_v1.yaml`
- Discover candidate VASP modules:
  - `tools/hpc/discover_vasp_modules.sh --keyword vasp`
- VASP health check (quick):
  - `tools/hpc/check_vasp_installation.sh --module <compiler_module> --module <mpi_module> --module <vasp_module>`
- VASP health check (smoke):
  - `tools/hpc/check_vasp_installation.sh --module <compiler_module> --module <mpi_module> --module <vasp_module> --run-smoke true --potcar /path/to/POTCAR --launch-cmd "srun -n 1"`
- Frontend dry-run:
  - `tools/hpc/run_vasp_pipeline.sh --mode dryrun --config configs/stage1_y_host_validation_v1.yaml`
- Frontend smoke test:
  - `tools/hpc/run_vasp_pipeline.sh --mode smoke --config configs/stage1_y_host_validation_v1.yaml --compiler-module <compiler_module> --mpi-module <mpi_module> --vasp-module <vasp_module>`
- Parse VASP outputs to metrics:
  - `python tools/extract_metrics.py --run-dir results/runs/<run_id>`
- Regenerate run HTML report from JSON artifacts:
  - `python tools/generate_run_report.py --run-dir results/runs/<run_id>`
- Generate update deck:
  - `python tools/presentation/generate_lab_meeting_ppt.py --scan-root results --output-dir presentations --deck-title "Y vs Zr Update" --require-pdf`
