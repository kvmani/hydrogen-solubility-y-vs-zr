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

## 3) HPC/VASP Overview (Cluster-Agnostic)
Use the templates in:
- `hpc/slurm_templates/`
- `hpc/vasp_templates/`

Baseline flow:
1. Choose a stage and create/update a config in `configs/`.
2. Prepare VASP inputs (POSCAR, POTCAR, KPOINTS, INCAR template copy).
3. Create a run directory under `results/runs/<run_id>/inputs/`.
4. Submit with a SLURM template adapted to your environment.
5. Archive scheduler logs and raw outputs into run folders.
6. Write `manifest.json` + `metrics.json`.

## 4) First Intended Milestone
Run Stage 1 host-only convergence tests for alpha-Y and alpha-Zr using identical methodological logic and explicit provenance.

## 5) What Not To Do
- Do not run undocumented calculations.
- Do not overwrite old runs; create a new run ID.
- Do not claim scientific conclusions without source citations and converged evidence.
