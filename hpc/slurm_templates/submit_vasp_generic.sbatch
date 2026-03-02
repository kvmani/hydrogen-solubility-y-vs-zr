#!/usr/bin/env bash
#SBATCH --job-name=<run_id>
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --time=08:00:00
#SBATCH --partition=<partition>
#SBATCH --account=<account>

set -Eeuo pipefail

if command -v module >/dev/null 2>&1; then
  module purge
  module load <compiler_module>
  module load <mpi_module>
  module load <vasp_module>
else
  echo "module command unavailable; skipping module setup"
fi

export OMP_NUM_THREADS=1

# Expected working directory is a run raw folder containing INCAR/POSCAR/KPOINTS/POTCAR.
RUN_DIR="${SLURM_SUBMIT_DIR}"
cd "${RUN_DIR}"

echo "Running in ${RUN_DIR}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-none}"

# Optional smoke gate used by tools/hpc/run_vasp_pipeline.sh
if [[ "${VASP_PIPELINE_SMOKE_ONLY:-0}" == "1" ]]; then
  echo "Smoke-only mode enabled; exiting before VASP launch."
  exit 0
fi

# Example launch command. Adapt to your cluster policy.
srun --mpi=pmix_v3 vasp_std > vasp.out 2> vasp.err
