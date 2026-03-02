#!/usr/bin/env bash
# Discover VASP-related module names and binary paths on an HPC system.

set -Eeuo pipefail

KEYWORD="vasp"
WORKDIR=""
KEEP_WORKDIR="true"
TRY_LOAD_MODULES=()
MODULE_INIT_ONLY="false"

usage() {
  cat <<'USAGE'
Usage: tools/hpc/discover_vasp_modules.sh [options]

Examples:
  tools/hpc/discover_vasp_modules.sh
  tools/hpc/discover_vasp_modules.sh --keyword vasp --keyword intel
  tools/hpc/discover_vasp_modules.sh --try-load vasp/6.4 --try-load vasp/6.3

Options:
  --keyword <term>          Search keyword for module discovery (default: vasp). Repeatable.
  --try-load <module>       Try loading this module and capture binary resolution. Repeatable.
  --workdir <path>          Output directory (default: /tmp/hsol_vasp_discovery_<ts>)
  --keep-workdir true|false Keep workdir after script ends (default: true)
  --module-init-only true|false
                            Only test module command initialization and exit
  --help                    Show this help
USAGE
}

KEYWORDS=()

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

run_module_cmd() {
  local outfile="$1"
  shift
  set +e
  module "$@" >"$outfile" 2>&1
  local rc=$?
  set -e
  return "$rc"
}

probe_binaries() {
  local out="$1"
  {
    echo "PATH=$PATH"
    for bin in vasp_std vasp_gam vasp_ncl vasp; do
      echo "--- binary: $bin ---"
      command -v "$bin" || true
      type -a "$bin" 2>/dev/null || true
      whereis "$bin" 2>/dev/null || true
    done
  } > "$out"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keyword)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --keyword" >&2; exit 1; }
      KEYWORDS+=("$2")
      shift 2
      ;;
    --try-load)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --try-load" >&2; exit 1; }
      TRY_LOAD_MODULES+=("$2")
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
    --module-init-only)
      [[ -n "${2-}" ]] || { echo "ERROR: Missing value for --module-init-only" >&2; exit 1; }
      MODULE_INIT_ONLY="$(parse_bool "$2")"
      [[ "$MODULE_INIT_ONLY" != "invalid" ]] || { echo "ERROR: --module-init-only expects true|false" >&2; exit 1; }
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

if [[ ${#KEYWORDS[@]} -eq 0 ]]; then
  KEYWORDS=("$KEYWORD")
fi

if [[ -z "$WORKDIR" ]]; then
  WORKDIR="/tmp/hsol_vasp_discovery_$(date -u +"%Y%m%dT%H%M%SZ")"
fi
mkdir -p "$WORKDIR"
WORKDIR="$(cd "$WORKDIR" && pwd -P)"

log "INFO" "Starting module discovery"
log "INFO" "Host: $(hostname)"
log "INFO" "Workdir: $WORKDIR"

if ! ensure_module_cmd; then
  log "ERROR" "module command not available after initialization attempts"
  log "ERROR" "Ask HPC support how modules are initialized in non-interactive shells"
  exit 2
fi

log "INFO" "module command is available"

if [[ "$MODULE_INIT_ONLY" == "true" ]]; then
  log "INFO" "Module init check done (--module-init-only true)"
  exit 0
fi

# Save baseline module state.
run_module_cmd "$WORKDIR/module_list_baseline.txt" list || true
run_module_cmd "$WORKDIR/module_avail_all.txt" -t avail || true

for kw in "${KEYWORDS[@]}"; do
  run_module_cmd "$WORKDIR/module_avail_${kw}.txt" -t avail "$kw" || true
  run_module_cmd "$WORKDIR/module_keyword_${kw}.txt" keyword "$kw" || true
  run_module_cmd "$WORKDIR/module_spider_${kw}.txt" spider "$kw" || true
done

probe_binaries "$WORKDIR/binary_probe_without_extra_loads.txt"

# Optional module load tests.
if [[ ${#TRY_LOAD_MODULES[@]} -gt 0 ]]; then
  for mod in "${TRY_LOAD_MODULES[@]}"; do
    safe_mod="$(printf '%s' "$mod" | tr '/ :' '___')"
    out_dir="$WORKDIR/try_load_${safe_mod}"
    mkdir -p "$out_dir"

    run_module_cmd "$out_dir/module_purge.txt" purge || true
    if run_module_cmd "$out_dir/module_load.txt" load "$mod"; then
      run_module_cmd "$out_dir/module_list_after_load.txt" list || true
      probe_binaries "$out_dir/binary_probe.txt"
      for bin in vasp_std vasp_gam vasp_ncl; do
        if command -v "$bin" >/dev/null 2>&1; then
          resolved="$(command -v "$bin")"
          if command -v ldd >/dev/null 2>&1; then
            ldd "$resolved" > "$out_dir/ldd_${bin}.txt" 2>&1 || true
          elif command -v otool >/dev/null 2>&1; then
            otool -L "$resolved" > "$out_dir/otool_${bin}.txt" 2>&1 || true
          fi
        fi
      done
    fi
  done
fi

SUMMARY="$WORKDIR/README.md"
{
  echo "# VASP Module Discovery Report"
  echo
  echo "- timestamp_utc: $(log_ts)"
  echo "- host: $(hostname)"
  echo "- workdir: $WORKDIR"
  echo "- keywords: ${KEYWORDS[*]}"
  if [[ ${#TRY_LOAD_MODULES[@]} -gt 0 ]]; then
    echo "- try_load_modules: ${TRY_LOAD_MODULES[*]}"
  else
    echo "- try_load_modules: none"
  fi
  echo
  echo "## Key Files"
  echo "- module list baseline: module_list_baseline.txt"
  echo "- module avail (all): module_avail_all.txt"
  for kw in "${KEYWORDS[@]}"; do
    echo "- module avail ($kw): module_avail_${kw}.txt"
    echo "- module keyword ($kw): module_keyword_${kw}.txt"
    echo "- module spider ($kw): module_spider_${kw}.txt"
  done
  echo "- binary probe without extra module loads: binary_probe_without_extra_loads.txt"
  if [[ ${#TRY_LOAD_MODULES[@]} -gt 0 ]]; then
    echo
    echo "## Try-Load Directories"
    for mod in "${TRY_LOAD_MODULES[@]}"; do
      safe_mod="$(printf '%s' "$mod" | tr '/ :' '___')"
      echo "- try_load_${safe_mod}/"
    done
  fi
  echo
  echo "## Next Step"
  echo "Use the best candidate module from this report with:"
  echo '`tools/hpc/check_vasp_installation.sh --module <compiler> --module <mpi> --module <vasp> --run-smoke true --potcar /path/to/POTCAR --launch-cmd "srun -n 1"`'
} > "$SUMMARY"

log "INFO" "Discovery report generated: $SUMMARY"

if [[ "$KEEP_WORKDIR" == "false" ]]; then
  rm -rf "$WORKDIR"
  log "INFO" "Removed workdir due to --keep-workdir false"
fi
