#!/usr/bin/env bash
#SBATCH --job-name=20260302_Zr_stage1_dft_005
#SBATCH --output=/Users/anantatamukalaamrutha/python_projects/hydrogen_solubility/results/runs/20260302_Zr_stage1_dft_005/logs/slurm/slurm-%j.out
#SBATCH --error=/Users/anantatamukalaamrutha/python_projects/hydrogen_solubility/results/runs/20260302_Zr_stage1_dft_005/logs/slurm/slurm-%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --time=08:00:00
#SBATCH --partition=<partition>
#SBATCH --account=<account>

set -Eeuo pipefail
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] host=$(hostname) slurm_job_id=${SLURM_JOB_ID:-none} run_id=20260302_Zr_stage1_dft_005"

if command -v module >/dev/null 2>&1; then
  module purge
  # module load <compiler_module>
  # module load <mpi_module>
  # module load <vasp_module>
else
  echo "module command unavailable; skipping module setup"
fi

export OMP_NUM_THREADS=1
cd /Users/anantatamukalaamrutha/python_projects/hydrogen_solubility/results/runs/20260302_Zr_stage1_dft_005/raw
for req in INCAR POSCAR KPOINTS; do
  if [[ ! -f "$req" ]]; then
    echo "Missing required input in raw/: $req"
    exit 2
  fi
done

if [[ "${VASP_PIPELINE_SMOKE_ONLY:-0}" == "1" ]]; then
  echo "Smoke-only mode enabled; exiting before VASP launch."
  exit 0
fi

LAUNCH_COMMAND=srun\ --mpi=pmix_v3
VASP_BINARY=vasp_std
RUN_ID=20260302_Zr_stage1_dft_005
echo "Launch command: ${LAUNCH_COMMAND} ${VASP_BINARY}"
eval "${LAUNCH_COMMAND} ${VASP_BINARY} > vasp.out 2> vasp.err"
