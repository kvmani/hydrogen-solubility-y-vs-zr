# hpc/

## Purpose
Provide cluster-agnostic run templates and checklists for beginner-friendly VASP execution with reproducible records.

## Goes In
- Scheduler templates (`slurm_templates/`)
- VASP input templates (`vasp_templates/`)
- Execution/checklist documentation (`runbook.md`)

## Does NOT Go In
- Cluster secrets or personal account details
- Raw simulation outputs (store under `results/`)
- One-off scripts that bypass config/provenance rules

## Mission Link
Makes computational execution systematic and repeatable so scientific claims can be audited.
