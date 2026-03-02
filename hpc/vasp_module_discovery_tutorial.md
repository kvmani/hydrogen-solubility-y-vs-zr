# Tutorial: How To Find VASP Modules And Binaries On HPC

Use this when you know VASP exists on your cluster (other users run it), but you do not yet know the exact module names or binary paths.

## 1) Quick Summary
Goal is to identify:
1. Which module(s) provide VASP.
2. Which binary to use (`vasp_std`, `vasp_gam`, or `vasp_ncl`).
3. How to invoke it reliably in Slurm jobs.

## 2) Understand Module Systems First
Most clusters use either:
- Environment Modules (`module avail`, `module load`), or
- Lmod (`module spider`, `module keyword` also available).

If `module` is missing in your shell, initialize and test:
```bash
source /etc/profile
module --version
```
If still missing, ask admins how modules are initialized for non-interactive shells.

## 3) Automated Discovery (Recommended)
Run the discovery helper:

```bash
tools/hpc/discover_vasp_modules.sh --keyword vasp
```

This writes a report directory under `/tmp/hsol_vasp_discovery_<timestamp>/` with:
- `module_avail_vasp.txt`
- `module_keyword_vasp.txt`
- `module_spider_vasp.txt`
- `binary_probe_without_extra_loads.txt`
- `README.md` summary

If you want to test specific candidate modules:

```bash
tools/hpc/discover_vasp_modules.sh \
  --keyword vasp \
  --try-load vasp/6.4 \
  --try-load vasp/6.3
```

## 4) Manual Discovery Commands (If Needed)
```bash
module -t avail vasp
module keyword vasp
module spider vasp
```

Also check candidate compiler/MPI stacks:
```bash
module -t avail intel
module -t avail gcc
module -t avail openmpi
module -t avail impi
```

## 5) Verify Binary Path After Loading Modules
After `module load ...`:
```bash
command -v vasp_std
command -v vasp_gam
command -v vasp_ncl
type -a vasp_std
```

Interpretation:
- `vasp_std`: standard production binary (most common default).
- `vasp_gam`: Gamma-only optimized runs.
- `vasp_ncl`: non-collinear/SOC use cases.

For this project, default to `vasp_std` unless a specific stage requires otherwise.

## 6) Check Linked Libraries (Binary Health)
```bash
ldd $(command -v vasp_std)
```
You should not see `not found` lines.

## 7) Confirm In Actual Runtime Context
Clusters often differ between login shell and job shell. Verify in an interactive allocation:

```bash
salloc -N 1 -n 1 -t 00:10:00 -p <partition> -A <account>
module purge
module load <compiler_module> <mpi_module> <vasp_module>
command -v vasp_std
```

Then run project health check:
```bash
tools/hpc/check_vasp_installation.sh \
  --module <compiler_module> \
  --module <mpi_module> \
  --module <vasp_module> \
  --run-smoke true \
  --potcar /path/to/POTCAR \
  --launch-cmd "srun -n 1"
```

## 8) Choosing The Final Invocation In Slurm
Once module+binaries are verified, use the same modules in:
- `tools/hpc/run_vasp_pipeline.sh --compiler-module ... --mpi-module ... --vasp-module ...`

The rendered sbatch script will invoke:
- launch prefix: `srun --mpi=pmix_v3` (override with `--launch-command` if cluster requires)
- executable: `vasp_std` (override with `--vasp-binary`)

## 9) If You Still Cannot Find VASP
Send admins a concise request with evidence:
- outputs of `module avail vasp`, `module spider vasp`
- your account/project name
- example job from colleagues (if allowed)
- your intended binary (`vasp_std`) and required queue/account

Ask specifically:
- which module name/version to load,
- required compiler/MPI dependency modules,
- recommended `srun` flags for VASP.
