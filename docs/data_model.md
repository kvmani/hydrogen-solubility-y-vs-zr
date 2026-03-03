# Data Model (Baseline)

This project requires machine-readable outputs per run. Two JSON files are mandatory from the start.

Config inputs for these outputs are validated against `docs/config_schema.md`.

## 1) `manifest.json` (Provenance + Context)

Minimal schema:
```json
{
  "run_id": "20260302_Y_stage1_dft_001",
  "timestamp_utc": "2026-03-02T09:30:00Z",
  "stage": "stage1",
  "system": "Y",
  "code": {
    "engine": "VASP",
    "version": "<required>",
    "workflow_version": "0.1.0"
  },
  "git": {
    "commit": "<hash>",
    "dirty": false
  },
  "inputs": {
    "config_path": "configs/<file>.yaml",
    "functional": "PBE",
    "potcar_labels": ["<label>"],
    "encut_eV": 520,
    "kmesh": "<kx,ky,kz>",
    "smearing": "<scheme+value>"
  },
  "hpc": {
    "scheduler": "slurm",
    "job_id": "<id>",
    "nodes": 1,
    "ntasks": 32,
    "walltime": "08:00:00",
    "submission": {
      "sbatch_script": "results/runs/<run_id>/logs/slurm/<run_id>_<timestamp>.sbatch",
      "submit_command": "sbatch ...",
      "pipeline_log": "results/runs/<run_id>/logs/orchestrator/<timestamp>_<mode>/pipeline.log",
      "submission_recorded_utc": "2026-03-02T10:00:00Z"
    }
  },
  "paths": {
    "run_dir": "results/runs/<run_id>",
    "raw_dir": "results/runs/<run_id>/raw",
    "parsed_dir": "results/runs/<run_id>/parsed"
  },
  "execution_events": [
    {
      "timestamp_utc": "2026-03-02T09:40:00Z",
      "event": "dryrun_completed",
      "status": "ok",
      "mode": "dryrun",
      "message": "Dry-run completed successfully.",
      "log_path": "results/runs/<run_id>/logs/orchestrator/<timestamp>_dryrun/pipeline.log"
    }
  ],
  "last_update_utc": "2026-03-02T10:00:00Z"
}
```

## 2) `metrics.json` (Numerical Outputs + Checks)

Minimal schema:
```json
{
  "run_id": "20260302_Y_stage1_dft_001",
  "status": "success",
  "energetics": {
    "total_energy_eV": -123.456,
    "energy_per_atom_eV": -6.1728,
    "formation_energy_eV": null,
    "h_solution_energy_eV": null,
    "oszicar_final_e0_eV": -123.200
  },
  "checks": {
    "electronic_converged": true,
    "ionic_converged": true,
    "encut_converged": null,
    "kmesh_converged": null
  },
  "artifacts": {
    "outcar": "raw/OUTCAR",
    "oszicar": "raw/OSZICAR",
    "summary_table": "parsed/summary.csv"
  },
  "notes": "placeholder"
}
```

Extraction note:
- `tools/extract_metrics.py` populates this structure from `raw/OUTCAR` and `raw/OSZICAR`.

## Human Report Requirement
Each run should include a concise human-readable `report.html` summarizing:
- objective and config
- key energies/derived quantities
- convergence evidence
- pass/fail decisions and next action

Current implementation:
- `tools/init_run.py` now emits an initial `report.html`.
- `tools/extract_metrics.py --run-dir ...` refreshes `report.html` after parsing outputs.
- `tools/generate_run_report.py --run-dir ...` can regenerate from existing JSON artifacts.

## Major-Update Presentation Requirement
For major result sets/feature additions, generate and version:
- a deck manifest JSON (`presentations/*_manifest.json`)
- a `.pptx` deck (`presentations/*.pptx`)
- a `.pdf` export (`presentations/*.pdf`)

## Bootstrap Status Convention
When a run is initialized via `tools/init_run.py`, starter metrics should use:
- `status: "initialized"`

This status must be replaced with execution outcomes (e.g., `success`, `failed`) after parsing real VASP outputs.

Parser may also emit `status: "partial"` when energies are available but convergence cannot be fully confirmed.
