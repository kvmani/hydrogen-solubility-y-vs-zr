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
    "walltime": "08:00:00"
  },
  "paths": {
    "run_dir": "results/runs/<run_id>",
    "raw_dir": "results/runs/<run_id>/raw",
    "parsed_dir": "results/runs/<run_id>/parsed"
  }
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
    "h_solution_energy_eV": null
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

## Human Report Requirement (Future Stages)
Each run will also require a concise human-readable `report.html` summarizing:
- objective and config
- key energies/derived quantities
- convergence evidence
- pass/fail decisions and next action

The HTML report is mandatory for completed research runs in later tasks.
