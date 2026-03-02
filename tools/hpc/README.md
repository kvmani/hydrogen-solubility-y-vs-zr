# tools/hpc/

## Purpose
Provide robust, scriptable orchestration for VASP workflows on Slurm with dry-run-first safety and rich diagnostics.

## Goes In
- `run_vasp_pipeline.sh`: single-config orchestrator (`dryrun`, `smoke`, `submit`)
- `run_vasp_batch.sh`: batch launcher across multiple configs
- `submit_vasp_job.sh`: sbatch wrapper preserving submit-directory provenance
- `update_manifest_event.py`: manifest event + submission metadata updater

## Does NOT Go In
- Cluster-specific secrets (accounts, private module paths)
- Hard-coded one-off run scripts outside config/manifest flow
- Raw VASP outputs (store under `results/runs/<run_id>/raw`)

## Mission Link
This directory enforces reproducibility and failure transparency before expensive compute is consumed.
