#!/usr/bin/env bash
# Submit one rendered sbatch script while preserving submit-directory provenance.

set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: tools/hpc/submit_vasp_job.sh <sbatch_script>

Example:
  tools/hpc/submit_vasp_job.sh results/runs/<run_id>/logs/slurm/<run_id>_<ts>.sbatch
USAGE
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

resolve_existing_file() {
  local input_path="$1"
  if [[ "$input_path" == /* ]]; then
    [[ -f "$input_path" ]] || return 1
    printf '%s\n' "$input_path"
    return 0
  fi
  [[ -f "$input_path" ]] || return 1
  (
    cd "$(dirname "$input_path")"
    printf '%s/%s\n' "$(pwd -P)" "$(basename "$input_path")"
  )
}

if ! command -v sbatch >/dev/null 2>&1; then
  echo "ERROR: sbatch not found in PATH." >&2
  exit 1
fi

sbatch_script_in="$1"
shift

if ! sbatch_script="$(resolve_existing_file "$sbatch_script_in")"; then
  echo "ERROR: sbatch script not found: $sbatch_script_in" >&2
  exit 1
fi

submit_dir="$(pwd -P)"
export_args="ALL,HSOL_REPO_ROOT=${submit_dir},HSOL_SUBMIT_DIR=${submit_dir}"

cmd=(
  sbatch
  --export="$export_args"
  "$sbatch_script"
)

printf 'Submitting command: '
printf '%q ' "${cmd[@]}"
printf '\n'

"${cmd[@]}"
