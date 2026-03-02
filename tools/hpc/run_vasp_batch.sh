#!/usr/bin/env bash
# Batch launcher for multiple VASP configs using run_vasp_pipeline.sh.

set -Eeuo pipefail

MODE="dryrun"
CONTINUE_ON_ERROR="false"
RESULTS_ROOT_OVERRIDE=""
INCAR_TEMPLATE="relax"
INCAR_PATH=""
FORCE_INIT="false"
SKIP_INIT="false"
FORCE_INPUT_SYNC="false"
SKIP_SBATCH_TEST="false"
REQUIRE_POTCAR=""
LAUNCH_COMMAND="srun --mpi=pmix_v3"
VASP_BINARY="vasp_std"
COMPILER_MODULE=""
MPI_MODULE=""
VASP_MODULE=""
NOTE=""
SUMMARY_FILE=""

SCRIPT_PATH=""
SCRIPT_DIR=""
REPO_ROOT=""
PIPELINE_SCRIPT=""

usage() {
  cat <<'USAGE'
Usage: tools/hpc/run_vasp_batch.sh --mode <dryrun|smoke|submit> [options] <config1> [<config2> ...]

Options:
  --continue-on-error true|false     Continue on per-config failure (default: false)
  --summary-file <path>              Write TSV summary (default: results/batch_runs/<timestamp>_mode-<mode>.tsv)
  --results-root <path>              Optional override for results root
  --incar-template relax|static      INCAR template selection (default: relax)
  --incar-path <path>                Explicit INCAR file path
  --force-init true|false            Re-run init_run.py with --force (default: false)
  --skip-init true|false             Skip run bootstrap (default: false)
  --force-input-sync true|false      Overwrite inputs/INCAR from template/path (default: false)
  --require-potcar true|false        Force POTCAR checks
  --skip-sbatch-test true|false      Skip sbatch --test-only in smoke mode
  --launch-command "<cmd>"           Launch command prefix (default: srun --mpi=pmix_v3)
  --vasp-binary <name>               VASP executable name (default: vasp_std)
  --compiler-module <mod>            Optional module to load
  --mpi-module <mod>                 Optional module to load
  --vasp-module <mod>                Optional module to load
  --note <text>                      Optional event note propagated to each run

Example:
  tools/hpc/run_vasp_batch.sh --mode dryrun configs/stage1_y_host_validation_v1.yaml configs/stage1_zr_host_validation_v1.yaml
USAGE
}

log_ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log() {
  local level="$1"
  shift
  echo "[$(log_ts)] [$level] $*"
}

parse_bool() {
  local value
  value="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    true|false) echo "$value" ;;
    *) echo "invalid" ;;
  esac
}

resolve_script_path() {
  local src="$1"
  if command -v readlink >/dev/null 2>&1; then
    local resolved
    resolved="$(readlink -f "$src" 2>/dev/null || true)"
    if [[ -n "$resolved" ]]; then
      printf '%s\n' "$resolved"
      return 0
    fi
  fi
  (
    cd "$(dirname "$src")"
    printf '%s/%s\n' "$(pwd -P)" "$(basename "$src")"
  )
}

canonicalize_dir() {
  local raw="$1"
  [[ -n "$raw" && -d "$raw" ]] || return 1
  (
    cd "$raw"
    pwd -P
  )
}

is_repo_root() {
  local path="$1"
  [[ -d "$path/src/hydrogen_solubility" ]] && [[ -x "$path/tools/hpc/run_vasp_pipeline.sh" ]]
}

resolve_repo_root() {
  local candidate=""
  for raw in "${HSOL_REPO_ROOT:-}" "${SLURM_SUBMIT_DIR:-}" "$SCRIPT_DIR" "$(pwd -P)"; do
    [[ -z "$raw" ]] && continue
    if candidate="$(canonicalize_dir "$raw" 2>/dev/null)" && is_repo_root "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  if git -C "$SCRIPT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
    candidate="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
    if candidate="$(canonicalize_dir "$candidate" 2>/dev/null)" && is_repo_root "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  fi
  return 1
}

to_abs_path() {
  local raw="$1"
  if [[ "$raw" == /* ]]; then
    printf '%s\n' "$raw"
  else
    printf '%s\n' "$REPO_ROOT/$raw"
  fi
}

# Parse options.
configs=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --mode" >&2; exit 1; }
      MODE="$2"
      shift 2
      ;;
    --continue-on-error)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --continue-on-error" >&2; exit 1; }
      CONTINUE_ON_ERROR="$(parse_bool "$2")"
      [[ "$CONTINUE_ON_ERROR" != "invalid" ]] || { echo "ERROR: --continue-on-error expects true|false" >&2; exit 1; }
      shift 2
      ;;
    --summary-file)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --summary-file" >&2; exit 1; }
      SUMMARY_FILE="$2"
      shift 2
      ;;
    --results-root)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --results-root" >&2; exit 1; }
      RESULTS_ROOT_OVERRIDE="$2"
      shift 2
      ;;
    --incar-template)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --incar-template" >&2; exit 1; }
      INCAR_TEMPLATE="$2"
      shift 2
      ;;
    --incar-path)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --incar-path" >&2; exit 1; }
      INCAR_PATH="$2"
      shift 2
      ;;
    --force-init)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --force-init" >&2; exit 1; }
      FORCE_INIT="$(parse_bool "$2")"
      [[ "$FORCE_INIT" != "invalid" ]] || { echo "ERROR: --force-init expects true|false" >&2; exit 1; }
      shift 2
      ;;
    --skip-init)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --skip-init" >&2; exit 1; }
      SKIP_INIT="$(parse_bool "$2")"
      [[ "$SKIP_INIT" != "invalid" ]] || { echo "ERROR: --skip-init expects true|false" >&2; exit 1; }
      shift 2
      ;;
    --force-input-sync)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --force-input-sync" >&2; exit 1; }
      FORCE_INPUT_SYNC="$(parse_bool "$2")"
      [[ "$FORCE_INPUT_SYNC" != "invalid" ]] || { echo "ERROR: --force-input-sync expects true|false" >&2; exit 1; }
      shift 2
      ;;
    --require-potcar)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --require-potcar" >&2; exit 1; }
      REQUIRE_POTCAR="$(parse_bool "$2")"
      [[ "$REQUIRE_POTCAR" != "invalid" ]] || { echo "ERROR: --require-potcar expects true|false" >&2; exit 1; }
      shift 2
      ;;
    --skip-sbatch-test)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --skip-sbatch-test" >&2; exit 1; }
      SKIP_SBATCH_TEST="$(parse_bool "$2")"
      [[ "$SKIP_SBATCH_TEST" != "invalid" ]] || { echo "ERROR: --skip-sbatch-test expects true|false" >&2; exit 1; }
      shift 2
      ;;
    --launch-command)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --launch-command" >&2; exit 1; }
      LAUNCH_COMMAND="$2"
      shift 2
      ;;
    --vasp-binary)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --vasp-binary" >&2; exit 1; }
      VASP_BINARY="$2"
      shift 2
      ;;
    --compiler-module)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --compiler-module" >&2; exit 1; }
      COMPILER_MODULE="$2"
      shift 2
      ;;
    --mpi-module)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --mpi-module" >&2; exit 1; }
      MPI_MODULE="$2"
      shift 2
      ;;
    --vasp-module)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --vasp-module" >&2; exit 1; }
      VASP_MODULE="$2"
      shift 2
      ;;
    --note)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --note" >&2; exit 1; }
      NOTE="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --*)
      echo "ERROR: Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      configs+=("$1")
      shift
      ;;
  esac
done

case "$MODE" in
  dryrun|smoke|submit) ;;
  *) echo "ERROR: --mode must be dryrun|smoke|submit" >&2; exit 1 ;;
esac

[[ ${#configs[@]} -gt 0 ]] || { echo "ERROR: Provide at least one config path." >&2; usage; exit 1; }

SCRIPT_PATH="$(resolve_script_path "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"

if ! REPO_ROOT="$(resolve_repo_root)"; then
  echo "ERROR: unable to resolve repository root." >&2
  exit 1
fi

PIPELINE_SCRIPT="$REPO_ROOT/tools/hpc/run_vasp_pipeline.sh"
[[ -x "$PIPELINE_SCRIPT" ]] || { echo "ERROR: missing executable pipeline script: $PIPELINE_SCRIPT" >&2; exit 1; }

if [[ -z "$SUMMARY_FILE" ]]; then
  ts="$(date -u +"%Y%m%dT%H%M%SZ")"
  SUMMARY_FILE="$REPO_ROOT/results/batch_runs/${ts}_mode-${MODE}.tsv"
else
  SUMMARY_FILE="$(to_abs_path "$SUMMARY_FILE")"
fi
mkdir -p "$(dirname "$SUMMARY_FILE")"

printf 'timestamp_utc\tconfig_path\tmode\tstatus\texit_code\n' > "$SUMMARY_FILE"

log "INFO" "Batch mode=$MODE configs=${#configs[@]} summary=$SUMMARY_FILE"

for cfg in "${configs[@]}"; do
  cfg_abs="$(to_abs_path "$cfg")"
  [[ -f "$cfg_abs" ]] || {
    log "ERROR" "Config not found: $cfg_abs"
    printf '%s\t%s\t%s\t%s\t%s\n' "$(log_ts)" "$cfg_abs" "$MODE" "failed" "2" >> "$SUMMARY_FILE"
    if [[ "$CONTINUE_ON_ERROR" == "true" ]]; then
      continue
    fi
    exit 2
  }

  cmd=("$PIPELINE_SCRIPT" "--mode" "$MODE" "--config" "$cfg_abs" "--incar-template" "$INCAR_TEMPLATE" "--force-init" "$FORCE_INIT" "--skip-init" "$SKIP_INIT" "--force-input-sync" "$FORCE_INPUT_SYNC" "--skip-sbatch-test" "$SKIP_SBATCH_TEST" "--launch-command" "$LAUNCH_COMMAND" "--vasp-binary" "$VASP_BINARY")

  if [[ -n "$RESULTS_ROOT_OVERRIDE" ]]; then
    cmd+=("--results-root" "$RESULTS_ROOT_OVERRIDE")
  fi
  if [[ -n "$INCAR_PATH" ]]; then
    cmd+=("--incar-path" "$INCAR_PATH")
  fi
  if [[ -n "$REQUIRE_POTCAR" ]]; then
    cmd+=("--require-potcar" "$REQUIRE_POTCAR")
  fi
  if [[ -n "$COMPILER_MODULE" ]]; then
    cmd+=("--compiler-module" "$COMPILER_MODULE")
  fi
  if [[ -n "$MPI_MODULE" ]]; then
    cmd+=("--mpi-module" "$MPI_MODULE")
  fi
  if [[ -n "$VASP_MODULE" ]]; then
    cmd+=("--vasp-module" "$VASP_MODULE")
  fi
  if [[ -n "$NOTE" ]]; then
    cmd+=("--note" "$NOTE")
  fi

  log "INFO" "Running config: $cfg_abs"

  set +e
  "${cmd[@]}"
  rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    printf '%s\t%s\t%s\t%s\t%s\n' "$(log_ts)" "$cfg_abs" "$MODE" "ok" "$rc" >> "$SUMMARY_FILE"
    log "INFO" "Config completed: $cfg_abs"
  else
    printf '%s\t%s\t%s\t%s\t%s\n' "$(log_ts)" "$cfg_abs" "$MODE" "failed" "$rc" >> "$SUMMARY_FILE"
    log "ERROR" "Config failed (rc=$rc): $cfg_abs"
    if [[ "$CONTINUE_ON_ERROR" != "true" ]]; then
      log "ERROR" "Aborting batch after first failure."
      exit "$rc"
    fi
  fi
done

log "INFO" "Batch completed. Summary: $SUMMARY_FILE"
