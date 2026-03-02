#!/bin/bash
#SBATCH --job-name=<run_id>
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=<ntasks>
#SBATCH --time=08:00:00
#SBATCH --partition=<partition>
#SBATCH --account=<account>

set -euo pipefail

# TODO: replace these with your HPC module/environment commands.
module purge
module load <compiler_module>
module load <mpi_module>
module load <vasp_module>

export OMP_NUM_THREADS=1

RUN_DIR="${SLURM_SUBMIT_DIR}"
cd "${RUN_DIR}"

echo "Running in ${RUN_DIR}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID}"

# Example launch command. Adapt to your cluster policy.
srun --mpi=pmix_v3 vasp_std > vasp.out
