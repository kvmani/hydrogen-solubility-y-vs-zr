# Getting Started

## 1) Local Bootstrap
1. Create and activate a Python environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Confirm baseline targets:
   - `make lint`
   - `make test`
   - `make docs-check`

## 2) Read Before Running Anything
- `mission_goals.md`
- `agents.md`
- `docs/roadmap.md`
- `docs/conventions.md`
- `docs/data_model.md`
- `literature/benchmarks/README.md`

## 3) HPC/VASP Overview (Cluster-Agnostic)
Use the templates in:
- `hpc/slurm_templates/`
- `hpc/vasp_templates/`

Baseline flow:
1. Choose a stage and create/update a config in `configs/`.
2. Validate config syntax + schema:
   - `python tools/validate_config.py <config-file>`
3. Initialize run directory + starter artifacts:
   - `python tools/init_run.py <config-file>`
4. Prepare VASP inputs (POSCAR, POTCAR, KPOINTS, INCAR template copy) in run `inputs/`.
5. Submit with a SLURM template adapted to your environment.
6. Archive scheduler logs and raw outputs into run folders.
7. Update `manifest.json` + `metrics.json` with real run metadata/results.

## 4) First Intended Milestone
Run Stage 1 host-only convergence tests for alpha-Y and alpha-Zr using identical methodological logic and explicit provenance.

## 5) Dissemination Deck Generation
For any major result/feature update, generate a discussion deck:
- `python tools/presentation/generate_lab_meeting_ppt.py --scan-root results --output-dir presentations --deck-title \"Y vs Zr Update\" --require-pdf`

This command creates a manifest, `.pptx`, and `.pdf` (LibreOffice `soffice` required for PDF conversion).

## 6) What Not To Do
- Do not run undocumented calculations.
- Do not overwrite old runs; create a new run ID.
- Do not claim scientific conclusions without source citations and converged evidence.
