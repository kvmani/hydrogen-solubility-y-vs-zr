# HPC Setup (once per cluster)

Goal: `./hsol doctor` reports no problems and `./hsol run --mode smoke` passes for one run.
About 30 minutes the first time.

## 1. Get the code and Python packages

```bash
git clone <repository-url> hydrogen-solubility && cd hydrogen-solubility
python3 -m venv .venv && source .venv/bin/activate    # Python >= 3.9
pip install -r requirements.txt
./hsol --help
```

Put the clone on a file system that compute nodes can see (home or project space), because jobs
call `./hsol collect` when VASP finishes. Run directories can live elsewhere (see step 3).

## 2. Find VASP on the cluster

```bash
tools/hpc/discover_vasp_modules.sh --keyword vasp          # writes a report in /tmp/hsol_vasp_discovery_*/
```

Manual equivalents: `module avail vasp`, `module spider vasp` (Lmod), then after loading a
candidate, `command -v vasp_std` and `ldd $(command -v vasp_std)` (no `not found` lines).
Note the compiler and MPI modules the VASP module needs.

Verify the candidate stack with a one-atom calculation, preferably inside a short interactive
allocation (many sites forbid MPI programs on login nodes):

```bash
salloc -N 1 -n 1 -t 00:10:00 -p <partition> -A <account>
tools/hpc/check_vasp_installation.sh --module <compiler> --module <mpi> --module <vasp> \
    --run-smoke true --potcar /path/to/potpaw_PBE/Zr_sv/POTCAR --launch-cmd "srun -n 1"
```

It reports the resolved binary, missing libraries and the VASP version. If you cannot find VASP,
send your admins the discovery report and ask which modules, binary and `srun` flags to use.

## 3. Write `configs/site.yaml`

```bash
cp configs/site.example.yaml configs/site.yaml
```

| Setting | What to put there |
|---|---|
| `slurm.partition`, `slurm.account` | values you use in `sbatch -p ... -A ...` (`sinfo -s`, `sacctmgr show assoc user=$USER`) |
| `slurm.extra_directives` | site-required options, e.g. `["--qos=normal"]` |
| `environment.modules` | the module list verified in step 2, in load order |
| `environment.login_shell` | `true` only if `module` is unknown inside jobs |
| `vasp.launch_command` | `srun` (default) or e.g. `mpirun -np $SLURM_NTASKS` |
| `vasp.potcar_root` | folder containing `Y_sv/POTCAR`, `Zr_sv/POTCAR`, `H/POTCAR` (PBE PAW, e.g. `potpaw_PBE.64`) |
| `paths.results_root` | `results/runs` (default) or an absolute path on project/scratch storage |

`configs/site.yaml` is ignored by git. POTCAR files are licensed by VASP: they are read from
`potcar_root` and never copied into git; manifests store only their TITEL, ENMAX and SHA-256.

## 4. Check

```bash
./hsol doctor
./hsol plan configs/campaigns/stage1_convergence.yaml
./hsol prepare configs/generated/stage1_convergence/Y_stage1_ref.yaml
./hsol run --mode dryrun configs/generated/stage1_convergence/Y_stage1_ref.yaml
./hsol run --mode smoke  configs/generated/stage1_convergence/Y_stage1_ref.yaml
```

The smoke test loads your modules, finds the VASP binary and launcher, and asks Slurm to validate
the resource request with `sbatch --test-only`, all without running VASP. When it passes you are
ready for [the workflow](workflow.md).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `doctor`: POTCAR not found | `potcar_root` must be the folder that *contains* `Y_sv/`, not `Y_sv/` itself. |
| smoke: `VASP binary 'vasp_std' not found` | Wrong or missing `environment.modules`; check `logs/<stamp>_smoke/smoke_local.log`. |
| smoke: `environment modules not available` warning, then binary not found | Set `environment.login_shell: true`. |
| smoke: `sbatch --test-only` rejected | Partition/account/walltime/ntasks not allowed; the log shows Slurm's reason. |
| job fails immediately, `slurm-<id>.err` mentions MPI/PMI | Adjust `vasp.launch_command` (e.g. `srun --mpi=pmix`) as your site documents. |
| `logs/slurm-<id>.out` says `automatic collect failed` | The job could not run Python; run `./hsol collect` on the login node. |
