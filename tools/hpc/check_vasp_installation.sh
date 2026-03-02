#!/usr/bin/env bash
# Basic VASP environment + smoke validation for HPC/frontend usage.

set -Eeuo pipefail

VASP_BINARY="vasp_std"
RUN_SMOKE="false"
POTCAR_PATH=""
WORKDIR=""
KEEP_WORKDIR="true"
LAUNCH_CMD=""
MODULES=()

usage() {
  cat <<'USAGE'
Usage: tools/hpc/check_vasp_installation.sh [options]

Quick environment check (binary + linked libraries):
  tools/hpc/check_vasp_installation.sh --vasp-binary vasp_std

Check with module loads:
  tools/hpc/check_vasp_installation.sh --module intel --module impi --module vasp/6.4

Smoke run (tiny static test) using an existing POTCAR:
  tools/hpc/check_vasp_installation.sh \
    --run-smoke true \
    --potcar /path/to/POTCAR \
    --workdir /scratch/$USER/vasp_smoke_check \
    --launch-cmd "srun -n 1"

Options:
  --vasp-binary <name>       VASP executable name (default: vasp_std)
  --module <name>            Module to load; repeat to load multiple modules
  --run-smoke true|false     Run a tiny VASP test calculation (default: false)
  --potcar <path>            POTCAR file path (required if --run-smoke true)
  --launch-cmd "<cmd>"       Optional launcher prefix for smoke run (e.g., "srun -n 1")
  --workdir <path>           Directory for check artifacts (default: /tmp/hsol_vasp_check_<ts>)
  --keep-workdir true|false  Keep generated files after run (default: true)
  --help                     Show this help
USAGE
}

log_ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log() {
  local level="$1"
  shift
  printf '[%s] [%s] %s\n' "$(log_ts)" "$level" "$*"
}

parse_bool() {
  local value
  value="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    true|false) echo "$value" ;;
    *) echo "invalid" ;;
  esac
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

ensure_module_cmd() {
  if have_cmd module; then
    return 0
  fi

  # shellcheck disable=SC1091
  for init_script in /etc/profile.d/modules.sh /usr/share/Modules/init/bash /usr/share/lmod/lmod/init/bash; do
    if [[ -f "$init_script" ]]; then
      # shellcheck disable=SC1090
      source "$init_script" >/dev/null 2>&1 || true
      if have_cmd module; then
        return 0
      fi
    fi
  done

  return 1
}

run_smoke_case() {
  local smoke_dir="$1"

  [[ -f "$POTCAR_PATH" ]] || {
    log "ERROR" "POTCAR not found: $POTCAR_PATH"
    return 2
  }

  mkdir -p "$smoke_dir"

  cat > "$smoke_dir/POSCAR" <<'POS'
VASP smoke check (Al, 1 atom)
1.0
4.05 0.00 0.00
0.00 4.05 0.00
0.00 0.00 4.05
Al
1
Direct
0.0 0.0 0.0
POS

  cat > "$smoke_dir/KPOINTS" <<'KPT'
Gamma mesh
0
Gamma
1 1 1
0 0 0
KPT

  cat > "$smoke_dir/INCAR" <<'INCAR'
SYSTEM = vasp_smoke_check
PREC   = Normal
ENCUT  = 350
ISMEAR = 1
SIGMA  = 0.2
EDIFF  = 1E-4
NELM   = 20
IBRION = -1
NSW    = 0
LREAL  = Auto
LWAVE  = .FALSE.
LCHARG = .FALSE.
INCAR

  cp -f "$POTCAR_PATH" "$smoke_dir/POTCAR"

  log "INFO" "Running smoke test in: $smoke_dir"

  local rc=0
  if [[ -n "$LAUNCH_CMD" ]]; then
    (
      cd "$smoke_dir"
      bash -lc "$LAUNCH_CMD $VASP_BINARY > vasp.stdout 2> vasp.stderr"
    ) || rc=$?
  else
    (
      cd "$smoke_dir"
      "$VASP_BINARY" > vasp.stdout 2> vasp.stderr
    ) || rc=$?
  fi

  if [[ "$rc" -ne 0 ]]; then
    log "ERROR" "Smoke run failed with exit code $rc"
    if [[ -f "$smoke_dir/vasp.stderr" ]]; then
      log "ERROR" "First stderr lines:"
      sed -n '1,20p' "$smoke_dir/vasp.stderr" || true
    fi
    return "$rc"
  fi

  [[ -s "$smoke_dir/OUTCAR" ]] || {
    log "ERROR" "Smoke run did not produce OUTCAR"
    return 3
  }

  if ! grep -q "General timing and accounting informations for this job" "$smoke_dir/OUTCAR"; then
    log "ERROR" "OUTCAR does not show normal end-of-run marker"
    return 4
  fi

  if grep -qi "VERY BAD NEWS" "$smoke_dir/OUTCAR"; then
    log "ERROR" "OUTCAR indicates a severe VASP internal error"
    return 5
  fi

  log "INFO" "Smoke run completed successfully"
  return 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vasp-binary)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --vasp-binary" >&2; exit 1; }
      VASP_BINARY="$2"
      shift 2
      ;;
    --module)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --module" >&2; exit 1; }
      MODULES+=("$2")
      shift 2
      ;;
    --run-smoke)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --run-smoke" >&2; exit 1; }
      RUN_SMOKE="$(parse_bool "$2")"
      [[ "$RUN_SMOKE" != "invalid" ]] || { echo "ERROR: --run-smoke expects true|false" >&2; exit 1; }
      shift 2
      ;;
    --potcar)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --potcar" >&2; exit 1; }
      POTCAR_PATH="$2"
      shift 2
      ;;
    --launch-cmd)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --launch-cmd" >&2; exit 1; }
      LAUNCH_CMD="$2"
      shift 2
      ;;
    --workdir)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --workdir" >&2; exit 1; }
      WORKDIR="$2"
      shift 2
      ;;
    --keep-workdir)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --keep-workdir" >&2; exit 1; }
      KEEP_WORKDIR="$(parse_bool "$2")"
      [[ "$KEEP_WORKDIR" != "invalid" ]] || { echo "ERROR: --keep-workdir expects true|false" >&2; exit 1; }
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

if [[ "$RUN_SMOKE" == "true" && -z "$POTCAR_PATH" ]]; then
  echo "ERROR: --potcar is required when --run-smoke true" >&2
  exit 1
fi

if [[ -z "$WORKDIR" ]]; then
  WORKDIR="/tmp/hsol_vasp_check_$(date -u +"%Y%m%dT%H%M%SZ")"
fi
mkdir -p "$WORKDIR"
WORKDIR="$(cd "$WORKDIR" && pwd -P)"

SUMMARY_JSON="$WORKDIR/vasp_check_summary.json"
MODULES_JSON="[]"

log "INFO" "Starting VASP environment check"
log "INFO" "Host: $(hostname)"
log "INFO" "Workdir: $WORKDIR"
log "INFO" "VASP binary target: $VASP_BINARY"

if [[ ${#MODULES[@]} -gt 0 ]]; then
  ensure_module_cmd || {
    log "ERROR" "module command not available; cannot load requested modules"
    exit 2
  }

  log "INFO" "Loading modules: ${MODULES[*]}"
  module purge >/dev/null 2>&1 || true
  for mod in "${MODULES[@]}"; do
    module load "$mod"
  done
fi

if [[ ${#MODULES[@]} -gt 0 ]]; then
  modules_joined="$(printf '\"%s\",' "${MODULES[@]}")"
  MODULES_JSON="[${modules_joined%,}]"
fi

if ! have_cmd "$VASP_BINARY"; then
  log "ERROR" "VASP executable not found in PATH: $VASP_BINARY"
  exit 3
fi

VASP_PATH="$(command -v "$VASP_BINARY")"
log "INFO" "Resolved VASP path: $VASP_PATH"

LIB_STATUS="unknown"
if have_cmd ldd; then
  ldd "$VASP_PATH" > "$WORKDIR/ldd_report.txt" 2>&1 || true
  if grep -q "not found" "$WORKDIR/ldd_report.txt"; then
    log "ERROR" "Missing shared libraries detected (see $WORKDIR/ldd_report.txt)"
    LIB_STATUS="failed"
    exit 4
  fi
  LIB_STATUS="ok"
elif have_cmd otool; then
  otool -L "$VASP_PATH" > "$WORKDIR/otool_report.txt" 2>&1 || true
  LIB_STATUS="ok"
else
  log "WARN" "Neither ldd nor otool found; skipping shared-library inspection"
fi

VERSION_PROBE="unsupported"
set +e
"$VASP_BINARY" --version > "$WORKDIR/version_probe.log" 2>&1
version_rc=$?
set -e
if [[ "$version_rc" -eq 0 ]]; then
  VERSION_PROBE="ok"
  log "INFO" "--version probe succeeded"
else
  log "WARN" "--version probe not supported (this is common for some VASP builds)"
fi

SMOKE_STATUS="skipped"
if [[ "$RUN_SMOKE" == "true" ]]; then
  SMOKE_STATUS="failed"
  if run_smoke_case "$WORKDIR/smoke_case"; then
    SMOKE_STATUS="ok"
  else
    SMOKE_STATUS="failed"
    exit 5
  fi
fi

cat > "$SUMMARY_JSON" <<JSON
{
  "timestamp_utc": "$(log_ts)",
  "host": "$(hostname)",
  "vasp_binary": "$VASP_BINARY",
  "vasp_path": "$VASP_PATH",
  "modules": $MODULES_JSON,
  "library_check": "$LIB_STATUS",
  "version_probe": "$VERSION_PROBE",
  "smoke_status": "$SMOKE_STATUS",
  "workdir": "$WORKDIR"
}
JSON

log "INFO" "Wrote summary: $SUMMARY_JSON"
log "INFO" "VASP check completed successfully"

if [[ "$KEEP_WORKDIR" == "false" ]]; then
  rm -rf "$WORKDIR"
  log "INFO" "Removed workdir due to --keep-workdir false"
fi
