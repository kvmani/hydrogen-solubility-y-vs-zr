# hpc/

## Purpose
Provide cluster-agnostic templates and operational runbooks for reproducible VASP execution on Slurm.

## Goes In
- Scheduler templates: `slurm_templates/`
- VASP input templates: `vasp_templates/`
- Operator guidance: `runbook.md`
- Beginner onboarding tutorial: `beginner_vasp_tutorial.md`

## Does NOT Go In
- Cluster credentials or private account details
- Raw simulation outputs (store under `results/`)
- Ad hoc scripts that bypass config + manifest contracts

## Mission Link
Defines the execution contract that turns documented methodology into auditable compute runs with dry-run-first safety.

## Related Orchestration Tools
- `tools/hpc/check_vasp_installation.sh`
- `tools/hpc/run_vasp_pipeline.sh`
- `tools/hpc/run_vasp_batch.sh`
- `tools/hpc/submit_vasp_job.sh`
