#!/usr/bin/env bash
# Robust single-run VASP pipeline orchestrator: dryrun -> smoke -> submit.

set -Eeuo pipefail

MODE="dryrun"                     # dryrun|smoke|submit
CONFIG_PATH=""
RESULTS_ROOT_OVERRIDE=""
INCAR_TEMPLATE="relax"            # relax|static
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
EVENT_NOTE=""

SCRIPT_PATH=""
SCRIPT_DIR=""
REPO_ROOT=""
PYTHON_BIN=""

RUN_ID=""
RUN_DIR=""
RESULTS_ROOT=""
NODES=""
NTASKS=""
WALLTIME=""
PARTITION=""
ACCOUNT=""
SYSTEM=""

SESSION_DIR=""
PIPELINE_LOG=""
SBATCH_SCRIPT=""

usage() {
  cat <<'USAGE'
Usage: tools/hpc/run_vasp_pipeline.sh --config <config.yaml> [options]

Core options:
  --mode dryrun|smoke|submit        Pipeline mode (default: dryrun)
  --config <path>                   Stage config path (required)
  --results-root <path>             Optional override for config outputs.results_root

Input deck options:
  --incar-template relax|static     Choose built-in INCAR template (default: relax)
  --incar-path <path>               Explicit INCAR path to copy into run inputs
  --force-input-sync true|false     Overwrite inputs/INCAR from template/path (default: false)
  --require-potcar true|false       Force POTCAR check in preflight (default: true in submit mode)

Scheduler/runtime options:
  --launch-command "<cmd>"          VASP launch command prefix (default: srun --mpi=pmix_v3)
  --vasp-binary <name>              VASP executable name (default: vasp_std)
  --compiler-module <mod>           Optional module to load in job script
  --mpi-module <mod>                Optional module to load in job script
  --vasp-module <mod>               Optional module to load in job script
  --skip-sbatch-test true|false     Skip sbatch --test-only during smoke mode (default: false)

Bootstrap options:
  --force-init true|false           Re-run tools/init_run.py --force (default: false)
  --skip-init true|false            Skip run bootstrap (default: false)
  --note <text>                     Optional note recorded in manifest events

Examples:
  tools/hpc/run_vasp_pipeline.sh --config configs/stage1_y_host_validation_v1.yaml --mode dryrun
  tools/hpc/run_vasp_pipeline.sh --config configs/stage1_y_host_validation_v1.yaml --mode smoke --compiler-module intel --mpi-module impi --vasp-module vasp/6.4
  tools/hpc/run_vasp_pipeline.sh --config configs/stage1_y_host_validation_v1.yaml --mode submit --require-potcar true
USAGE
}

log_ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log() {
  local level="$1"
  shift
  echo "[$(log_ts)] [$level] $*"
}

die() {
  log "ERROR" "$*"
  if [[ -n "$RUN_DIR" && -f "$RUN_DIR/manifest.json" && -n "$PIPELINE_LOG" ]]; then
    "$PYTHON_BIN" "$REPO_ROOT/tools/hpc/update_manifest_event.py" \
      --run-dir "$RUN_DIR" \
      --event "pipeline_failed" \
      --status "failed" \
      --mode "$MODE" \
      --message "$*" \
      --log-path "$PIPELINE_LOG" >/dev/null 2>&1 || true
  fi
  exit 1
}

on_error() {
  local rc=$?
  local line_no="$1"
  local cmd="$2"
  die "Command failed (rc=$rc) at line $line_no: $cmd"
}

trap 'on_error "$LINENO" "$BASH_COMMAND"' ERR

have_cmd() {
  command -v "$1" >/dev/null 2>&1
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
  if have_cmd readlink; then
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
  [[ -d "$path/src/hydrogen_solubility" ]] && [[ -f "$path/tools/init_run.py" ]] && [[ -f "$path/README.md" ]]
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

is_placeholder() {
  local value="$1"
  local lowered
  lowered="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  if [[ "$value" == \<*\> ]]; then
    return 0
  fi
  if [[ "$value" == *"<"* || "$value" == *">"* ]]; then
    return 0
  fi
  case "$lowered" in
    ""|placeholder|replace_me|tbd|todo) return 0 ;;
  esac
  return 1
}

record_event() {
  local event="$1"
  local status="$2"
  local message="$3"
  shift 3 || true

  if [[ -z "$RUN_DIR" || ! -f "$RUN_DIR/manifest.json" ]]; then
    return 0
  fi

  "$PYTHON_BIN" "$REPO_ROOT/tools/hpc/update_manifest_event.py" \
    --run-dir "$RUN_DIR" \
    --event "$event" \
    --status "$status" \
    --mode "$MODE" \
    --message "$message" \
    --log-path "$PIPELINE_LOG" \
    "$@" >/dev/null 2>&1 || true
}

ensure_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    return 0
  fi

  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
    return 0
  fi

  if have_cmd python3; then
    PYTHON_BIN="$(command -v python3)"
    return 0
  fi

  if have_cmd python; then
    PYTHON_BIN="$(command -v python)"
    return 0
  fi

  echo "ERROR: Python executable not found." >&2
  exit 1
}

# Parse args.
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --mode" >&2; exit 1; }
      MODE="$2"
      shift 2
      ;;
    --config)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --config" >&2; exit 1; }
      CONFIG_PATH="$2"
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
    --skip-sbatch-test)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --skip-sbatch-test" >&2; exit 1; }
      SKIP_SBATCH_TEST="$(parse_bool "$2")"
      [[ "$SKIP_SBATCH_TEST" != "invalid" ]] || { echo "ERROR: --skip-sbatch-test expects true|false" >&2; exit 1; }
      shift 2
      ;;
    --require-potcar)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --require-potcar" >&2; exit 1; }
      REQUIRE_POTCAR="$(parse_bool "$2")"
      [[ "$REQUIRE_POTCAR" != "invalid" ]] || { echo "ERROR: --require-potcar expects true|false" >&2; exit 1; }
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
      EVENT_NOTE="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

case "$MODE" in
  dryrun|smoke|submit) ;;
  *) echo "ERROR: --mode must be one of dryrun|smoke|submit" >&2; exit 1 ;;
esac

case "$INCAR_TEMPLATE" in
  relax|static) ;;
  *) echo "ERROR: --incar-template must be relax|static" >&2; exit 1 ;;
esac

[[ -n "$CONFIG_PATH" ]] || { echo "ERROR: --config is required" >&2; usage; exit 1; }

# Resolve repo context.
SCRIPT_PATH="$(resolve_script_path "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd -P)"

if ! REPO_ROOT="$(resolve_repo_root)"; then
  echo "ERROR: unable to resolve repository root." >&2
  echo "DEBUG SCRIPT_PATH: $SCRIPT_PATH" >&2
  echo "DEBUG SCRIPT_DIR: $SCRIPT_DIR" >&2
  echo "DEBUG PWD: $(pwd -P)" >&2
  echo "DEBUG HSOL_REPO_ROOT: ${HSOL_REPO_ROOT:-<unset>}" >&2
  echo "DEBUG SLURM_SUBMIT_DIR: ${SLURM_SUBMIT_DIR:-<unset>}" >&2
  exit 1
fi

cd "$REPO_ROOT"
ensure_python

CONFIG_ABS="$(to_abs_path "$CONFIG_PATH")"
[[ -f "$CONFIG_ABS" ]] || { echo "ERROR: config not found: $CONFIG_ABS" >&2; exit 1; }

# Validate config first.
"$PYTHON_BIN" "$REPO_ROOT/tools/validate_config.py" "$CONFIG_ABS" >/dev/null

# Load critical config fields.
cfg_env="$("$PYTHON_BIN" - "$CONFIG_ABS" "$REPO_ROOT" <<'PY'
from __future__ import annotations

import shlex
import sys
from pathlib import Path

config_path = Path(sys.argv[1]).resolve()
repo_root = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(repo_root / "src"))

from hydrogen_solubility.config_models import load_stage1_host_config

cfg = load_stage1_host_config(config_path)
payload = {
    "RUN_ID": cfg.run.run_id,
    "RESULTS_ROOT": cfg.outputs.results_root,
    "NODES": cfg.hpc.nodes,
    "NTASKS": cfg.hpc.ntasks,
    "WALLTIME": cfg.hpc.walltime,
    "PARTITION": cfg.hpc.partition,
    "ACCOUNT": cfg.hpc.account,
    "SYSTEM": cfg.run.system,
}
for key, value in payload.items():
    print(f"{key}={shlex.quote(str(value))}")
PY
)"

# shellcheck disable=SC2086
# Fields are shell-quoted by Python shlex.quote.
eval "$cfg_env"

if [[ -n "$RESULTS_ROOT_OVERRIDE" ]]; then
  RESULTS_ROOT="$RESULTS_ROOT_OVERRIDE"
else
  RESULTS_ROOT="$RESULTS_ROOT"
fi

if [[ "$RESULTS_ROOT" == /* ]]; then
  RESULTS_ROOT_ABS="$RESULTS_ROOT"
else
  RESULTS_ROOT_ABS="$REPO_ROOT/$RESULTS_ROOT"
fi

RUN_DIR="$RESULTS_ROOT_ABS/$RUN_ID"

if [[ "$SKIP_INIT" == "false" ]]; then
  if [[ ! -d "$RUN_DIR" || "$FORCE_INIT" == "true" ]]; then
    init_cmd=("$PYTHON_BIN" "$REPO_ROOT/tools/init_run.py" "$CONFIG_ABS")
    if [[ -n "$RESULTS_ROOT_OVERRIDE" ]]; then
      init_cmd+=(--results-root "$RESULTS_ROOT_ABS")
    fi
    if [[ "$FORCE_INIT" == "true" ]]; then
      init_cmd+=(--force)
    fi
    "${init_cmd[@]}" >/dev/null
  fi
fi

[[ -d "$RUN_DIR" ]] || { echo "ERROR: run directory missing: $RUN_DIR" >&2; exit 1; }

mkdir -p "$RUN_DIR/logs/orchestrator" "$RUN_DIR/logs/slurm" "$RUN_DIR/raw" "$RUN_DIR/inputs"

SESSION_STAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
SESSION_DIR="$RUN_DIR/logs/orchestrator/${SESSION_STAMP}_${MODE}"
mkdir -p "$SESSION_DIR"
PIPELINE_LOG="$SESSION_DIR/pipeline.log"

# Mirror output to terminal + log file.
exec > >(tee -a "$PIPELINE_LOG") 2>&1

log "INFO" "Pipeline start: mode=$MODE run_id=$RUN_ID system=$SYSTEM"
log "INFO" "Repo root: $REPO_ROOT"
log "INFO" "Config: $CONFIG_ABS"
log "INFO" "Run dir: $RUN_DIR"
log "INFO" "Python: $PYTHON_BIN"
if [[ -n "$EVENT_NOTE" ]]; then
  log "INFO" "Note: $EVENT_NOTE"
fi

if have_cmd git; then
  log "INFO" "Git commit: $(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
  log "INFO" "Git dirty: $(test -n "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null || true)" && echo true || echo false)"
fi

record_event "pipeline_started" "ok" "Pipeline mode=$MODE started."

if [[ -z "$REQUIRE_POTCAR" ]]; then
  if [[ "$MODE" == "submit" ]]; then
    REQUIRE_POTCAR="true"
  else
    REQUIRE_POTCAR="false"
  fi
fi

if [[ "$MODE" == "submit" ]]; then
  if is_placeholder "$PARTITION"; then
    die "hpc.partition still looks like a placeholder ($PARTITION). Update config before submit."
  fi
  if is_placeholder "$ACCOUNT"; then
    die "hpc.account still looks like a placeholder ($ACCOUNT). Update config before submit."
  fi
fi

# Resolve/copy INCAR.
if [[ -n "$INCAR_PATH" ]]; then
  INCAR_SRC="$(to_abs_path "$INCAR_PATH")"
else
  INCAR_SRC="$REPO_ROOT/hpc/vasp_templates/INCAR.$INCAR_TEMPLATE"
fi
[[ -f "$INCAR_SRC" ]] || die "INCAR source not found: $INCAR_SRC"

if [[ ! -f "$RUN_DIR/inputs/INCAR" || "$FORCE_INPUT_SYNC" == "true" ]]; then
  cp -f "$INCAR_SRC" "$RUN_DIR/inputs/INCAR"
  log "INFO" "INCAR copied to run inputs from: $INCAR_SRC"
else
  log "INFO" "Existing inputs/INCAR retained (use --force-input-sync true to overwrite)."
fi

required_inputs=("POSCAR" "KPOINTS" "INCAR")
if [[ "$REQUIRE_POTCAR" == "true" ]]; then
  required_inputs+=("POTCAR")
fi

raw_required_inputs="INCAR POSCAR KPOINTS"
if [[ "$REQUIRE_POTCAR" == "true" ]]; then
  raw_required_inputs+=" POTCAR"
fi

missing_inputs=()
for req in "${required_inputs[@]}"; do
  if [[ ! -f "$RUN_DIR/inputs/$req" ]]; then
    missing_inputs+=("$req")
  fi
done

if [[ ${#missing_inputs[@]} -gt 0 ]]; then
  msg="Missing input file(s) under $RUN_DIR/inputs: ${missing_inputs[*]}"
  if [[ "$MODE" == "dryrun" ]]; then
    log "WARN" "$msg"
  else
    die "$msg"
  fi
fi

# Sync available input deck files to raw/ for execution.
for deck_file in INCAR POSCAR KPOINTS POTCAR; do
  if [[ -f "$RUN_DIR/inputs/$deck_file" ]]; then
    cp -f "$RUN_DIR/inputs/$deck_file" "$RUN_DIR/raw/$deck_file"
  fi
done

printf -v raw_dir_q '%q' "$RUN_DIR/raw"
printf -v launch_q '%q' "$LAUNCH_COMMAND"
printf -v vasp_q '%q' "$VASP_BINARY"
printf -v run_id_q '%q' "$RUN_ID"

SBATCH_SCRIPT="$RUN_DIR/logs/slurm/${RUN_ID}_${SESSION_STAMP}.sbatch"

{
  echo "#!/usr/bin/env bash"
  echo "#SBATCH --job-name=$RUN_ID"
  echo "#SBATCH --output=$RUN_DIR/logs/slurm/slurm-%j.out"
  echo "#SBATCH --error=$RUN_DIR/logs/slurm/slurm-%j.err"
  echo "#SBATCH --nodes=$NODES"
  echo "#SBATCH --ntasks=$NTASKS"
  echo "#SBATCH --time=$WALLTIME"
  echo "#SBATCH --partition=$PARTITION"
  echo "#SBATCH --account=$ACCOUNT"
  echo
  echo "set -Eeuo pipefail"
  echo "echo \"[\$(date -u +%Y-%m-%dT%H:%M:%SZ)] host=\$(hostname) slurm_job_id=\${SLURM_JOB_ID:-none} run_id=$RUN_ID\""
  echo ""
  echo "if command -v module >/dev/null 2>&1; then"
  echo "  module purge"
  if [[ -n "$COMPILER_MODULE" ]]; then
    printf -v compiler_q '%q' "$COMPILER_MODULE"
    echo "  module load $compiler_q"
  else
    echo "  # module load <compiler_module>"
  fi
  if [[ -n "$MPI_MODULE" ]]; then
    printf -v mpi_q '%q' "$MPI_MODULE"
    echo "  module load $mpi_q"
  else
    echo "  # module load <mpi_module>"
  fi
  if [[ -n "$VASP_MODULE" ]]; then
    printf -v vasp_mod_q '%q' "$VASP_MODULE"
    echo "  module load $vasp_mod_q"
  else
    echo "  # module load <vasp_module>"
  fi
  echo "else"
  echo "  echo \"module command unavailable; skipping module setup\""
  echo "fi"
  echo
  echo "export OMP_NUM_THREADS=1"
  echo "cd $raw_dir_q"
  echo "for req in $raw_required_inputs; do"
  echo "  if [[ ! -f \"\$req\" ]]; then"
  echo "    echo \"Missing required input in raw/: \$req\""
  echo "    exit 2"
  echo "  fi"
  echo "done"
  echo
  echo "if [[ \"\${VASP_PIPELINE_SMOKE_ONLY:-0}\" == \"1\" ]]; then"
  echo "  echo \"Smoke-only mode enabled; exiting before VASP launch.\""
  echo "  exit 0"
  echo "fi"
  echo
  echo "LAUNCH_COMMAND=$launch_q"
  echo "VASP_BINARY=$vasp_q"
  echo "RUN_ID=$run_id_q"
  echo "echo \"Launch command: \${LAUNCH_COMMAND} \${VASP_BINARY}\""
  echo "eval \"\${LAUNCH_COMMAND} \${VASP_BINARY} > vasp.out 2> vasp.err\""
} > "$SBATCH_SCRIPT"

chmod +x "$SBATCH_SCRIPT"

log "INFO" "Rendered sbatch script: $SBATCH_SCRIPT"
record_event "preflight_ok" "ok" "Preflight checks completed." --sbatch-script "$SBATCH_SCRIPT"

# Validate script syntax.
bash -n "$SBATCH_SCRIPT"

if [[ "$MODE" == "dryrun" ]]; then
  log "INFO" "Dry-run complete. No scheduler submission executed."
  log "INFO" "Planned submit command: sbatch --export=ALL,HSOL_REPO_ROOT=$(pwd -P),HSOL_SUBMIT_DIR=$(pwd -P) $SBATCH_SCRIPT"
  record_event "dryrun_completed" "ok" "Dry-run completed successfully." --sbatch-script "$SBATCH_SCRIPT"
  exit 0
fi

if [[ "$MODE" == "smoke" ]]; then
  smoke_local_log="$SESSION_DIR/smoke_local.log"
  set +e
  VASP_PIPELINE_SMOKE_ONLY=1 bash "$SBATCH_SCRIPT" >"$smoke_local_log" 2>&1
  smoke_rc=$?
  set -e
  if [[ "$smoke_rc" -ne 0 ]]; then
    die "Smoke local execution failed (rc=$smoke_rc). See $smoke_local_log"
  fi
  log "INFO" "Smoke local execution passed: $smoke_local_log"

  if [[ "$SKIP_SBATCH_TEST" == "false" ]]; then
    if have_cmd sbatch; then
      if sbatch --help 2>&1 | grep -q -- '--test-only'; then
        sbatch_test_log="$SESSION_DIR/sbatch_test_only.log"
        set +e
        sbatch --test-only "$SBATCH_SCRIPT" >"$sbatch_test_log" 2>&1
        sbatch_test_rc=$?
        set -e
        if [[ "$sbatch_test_rc" -ne 0 ]]; then
          die "sbatch --test-only failed (rc=$sbatch_test_rc). See $sbatch_test_log"
        fi
        log "INFO" "sbatch --test-only passed: $sbatch_test_log"
      else
        log "WARN" "sbatch found but --test-only unsupported on this cluster; skipping scheduler syntax test."
      fi
    else
      log "WARN" "sbatch command not found; skipped scheduler smoke test."
    fi
  fi

  record_event "smoke_completed" "ok" "Smoke checks completed successfully." --sbatch-script "$SBATCH_SCRIPT"
  log "INFO" "Smoke workflow completed successfully."
  exit 0
fi

# MODE=submit
have_cmd sbatch || die "sbatch not found in PATH."
submit_wrapper="$REPO_ROOT/tools/hpc/submit_vasp_job.sh"
[[ -x "$submit_wrapper" ]] || die "Submit wrapper missing or not executable: $submit_wrapper"

set +e
submit_output="$($submit_wrapper "$SBATCH_SCRIPT" 2>&1)"
submit_rc=$?
set -e

printf '%s\n' "$submit_output"

if [[ "$submit_rc" -ne 0 ]]; then
  die "Scheduler submission failed (rc=$submit_rc)."
fi

job_id="$(printf '%s\n' "$submit_output" | sed -n 's/.*Submitted batch job \([0-9][0-9]*\).*/\1/p' | tail -n 1)"

submission_receipt="$SESSION_DIR/submission_receipt.txt"
printf '%s\n' "$submit_output" > "$submission_receipt"

submit_cmd_text="sbatch --export=ALL,HSOL_REPO_ROOT=$(pwd -P),HSOL_SUBMIT_DIR=$(pwd -P) $SBATCH_SCRIPT"

if [[ -n "$job_id" ]]; then
  log "INFO" "Submitted batch job id: $job_id"
  record_event "submit_completed" "ok" "Scheduler submission completed." \
    --sbatch-script "$SBATCH_SCRIPT" \
    --submit-command "$submit_cmd_text" \
    --job-id "$job_id"
else
  log "WARN" "Job id was not detected from sbatch output."
  record_event "submit_completed" "warn" "Submission command ran but job id could not be parsed." \
    --sbatch-script "$SBATCH_SCRIPT" \
    --submit-command "$submit_cmd_text"
fi

log "INFO" "Submission receipt: $submission_receipt"
log "INFO" "Submit workflow completed."
