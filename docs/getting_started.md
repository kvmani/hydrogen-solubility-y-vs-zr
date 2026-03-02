# Getting Started

## 1) Local Bootstrap
1. Create and activate a Python environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run baseline checks:
   - `make lint`
   - `make test`
   - `make docs-check`

## 2) Read Before Running Anything
- `mission_goals.md`
- `agents.md`
- `docs/roadmap.md`
- `docs/conventions.md`
- `docs/data_model.md`
- `hpc/beginner_vasp_tutorial.md`
- `hpc/vasp_module_discovery_tutorial.md`
- `hpc/runbook.md`
- `docs/stage1_campaign.md`

## 3) Baseline HPC Flow (Dry-Run First)
1. Discover module names (if unknown):
   - `tools/hpc/discover_vasp_modules.sh --keyword vasp`
2. Validate config:
   - `python tools/validate_config.py configs/stage1_y_host_validation_v1.yaml`
3. Initialize run folder:
   - `python tools/init_run.py configs/stage1_y_host_validation_v1.yaml`
4. Place inputs in `results/runs/<run_id>/inputs/`:
   - `POSCAR`, `KPOINTS`, `INCAR`, `POTCAR`
5. Frontend dry-run (no submission):
   - `tools/hpc/run_vasp_pipeline.sh --mode dryrun --config configs/stage1_y_host_validation_v1.yaml`
6. Frontend smoke checks:
   - `tools/hpc/run_vasp_pipeline.sh --mode smoke --config configs/stage1_y_host_validation_v1.yaml --compiler-module <compiler_module> --mpi-module <mpi_module> --vasp-module <vasp_module>`
7. Real submit:
   - `tools/hpc/run_vasp_pipeline.sh --mode submit --config configs/stage1_y_host_validation_v1.yaml --compiler-module <compiler_module> --mpi-module <mpi_module> --vasp-module <vasp_module> --require-potcar true`
8. Parse outputs after completion:
   - `python tools/extract_metrics.py --run-dir results/runs/<run_id>`

Batch orchestration:
- `tools/hpc/run_vasp_batch.sh --mode dryrun configs/stage1_y_host_validation_v1.yaml configs/stage1_zr_host_validation_v1.yaml`

## 4) Stage-1 Campaign Generation
Generate a full convergence config set (Y + Zr):
- `make plan-stage1`

Then follow `docs/stage1_campaign.md` to execute dry-run, smoke, and submit in batch.

## 5) First Intended Milestone
Run Stage-1 host-only validation for alpha-Y and alpha-Zr with matched convergence logic and full provenance.

## 6) Dissemination Deck Generation
For any major result/feature update, generate discussion decks:
- `python tools/presentation/generate_lab_meeting_ppt.py --scan-root results --output-dir presentations --deck-title "Y vs Zr Update" --require-pdf`

This writes a manifest, `.pptx`, and `.pdf` (LibreOffice `soffice` required for PDF conversion).

## 7) What Not To Do
- Do not submit real jobs before dry-run and smoke pass.
- Do not run undocumented one-off calculations.
- Do not overwrite historical runs; create a new `run_id`.
- Do not claim conclusions without converged evidence and primary citations.
