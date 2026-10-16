# Workflow

Everything is driven by one command, `./hsol` (run from the repository root; `hsol` if you
installed the package with `pip install -e .`). Every subcommand has `--help`.

## Quick reference

```bash
# once per machine (details: hpc_setup.md)
cp configs/site.example.yaml configs/site.yaml        # edit partition, account, modules, POTCAR path
./hsol doctor                                         # tells you what is still missing

# the loop, once per stage  (<c> = campaign name, e.g. stage1_convergence)
./hsol plan    configs/campaigns/<c>.yaml             # campaign -> configs/generated/<c>/*.yaml
./hsol prepare configs/generated/<c>                  # run dirs + INCAR/KPOINTS/POSCAR/POTCAR
./hsol run --mode dryrun configs/generated/<c>        # job scripts rendered and checked
./hsol run --mode smoke  configs/generated/<c>        # modules, binary, sbatch --test-only
./hsol run --mode submit configs/generated/<c>        # real Slurm jobs
./hsol status                                         # progress; writes results/INDEX.md
./hsol collect                                        # parse finished runs (jobs also do this)

# analysis
./hsol analyze convergence                            # after stage 1a
./hsol analyze solubility                             # after stages 2-4 (works with partial data)
```

## Stage by stage

Run the stages in this order. Each row's prerequisite must show `converged` in `./hsol status`.

| # | Campaign file | Needs | Check before moving on |
|---|---|---|---|
| 1a | `stage1_convergence.yaml` | site setup | `./hsol analyze convergence` gives a recommendation; copy it into `configs/campaigns/converged_settings.yaml` |
| 1b | `stage1_relax.yaml` | 1a | relaxed `a_A`, `c_A`, `c_over_a` in each `report.html`; compare with the experimental starting values noted in the campaign file |
| 2 | `stage2_h_energetics.yaml` | 1b | `hT`/`hO` reports show `site_preserved: yes`; if an O start relaxed to T, that is a result, not an error |
| 3 | `stage3_vibrations.yaml` | 2 | no imaginary modes for the sites you keep; H₂ stretch close to the experimental harmonic value 545.7 meV (4401 cm⁻¹, NIST) |
| 4a | `stage4_hydrides.yaml` | 1a (+1b for the bulk reference) | hydride relaxed, `cell_lengths_A` reasonable |
| 4b | `stage4_hydride_vibrations.yaml` | 4a | all 24 H modes real |
| 5 | `./hsol analyze solubility` | any of the above | `results/analysis/solubility/summary.md` lists no missing inputs |

Planning a production campaign (1b onwards) stops with a clear message until
`converged_settings.yaml` is filled in. Preparing a run whose parent (`lattice_from_run`,
`from_run`) is not yet converged also stops with a message naming the parent.

## What each command does

**plan** expands a campaign file (all systems at once) into one explicit, validated config per run
under `configs/generated/<campaign>/`, plus `plan.csv`. Generated configs are never edited by
hand; change the campaign file and plan again.

**prepare** creates `results/runs/<run_id>/` with the input deck, a config snapshot, a manifest
(git commit, environment, file hashes, POTCAR identities) and a starter report. It is idempotent:
unchanged configs are skipped, changed configs regenerate inputs **unless VASP outputs already
exist** — then you must give the run a new id (set `tag:` in the campaign).

**run** has three modes that must be passed in order for the *current* inputs:

| Mode | Checks | Side effects |
|---|---|---|
| `dryrun` | run prepared, config unchanged, job script renders and passes `bash -n` | session log only |
| `smoke` | POTCAR present, site config filled in, modules load, VASP binary and launcher found, `sbatch --test-only` accepts the request | scratch copy in the session folder; `raw/` untouched |
| `submit` | a smoke test passed for exactly these inputs and site settings; run not already submitted | inputs copied to `raw/`, `sbatch`, job id stored in the manifest |

Every invocation writes `logs/<UTC>_<mode>/pipeline.log` and the rendered `job.sbatch` in the run
directory and appends an event to `manifest.json`. A batch summary goes to `results/batch_logs/`.

**collect** parses `raw/OUTCAR`, `OSZICAR`, `CONTCAR` into `metrics.json`, stamps the VASP version
into the manifest, refreshes `report.html` and the results index. Jobs call it automatically when
VASP exits; run it by hand after manual fixes or if a job's Python environment was unavailable.

**status** prints every run with its status (and Slurm queue state on the cluster) and rewrites
`results/INDEX.md` and `results/index.csv`.

## Reading a run

| Status | Meaning | What to do |
|---|---|---|
| `prepared` | inputs exist, not submitted | dryrun → smoke → submit |
| `submitted` | job id recorded | wait; `status` shows PENDING/RUNNING |
| `incomplete` | VASP did not finish (walltime, crash) | read `logs/slurm-<job>.err` and `raw/vasp.err` |
| `unconverged` | finished, but SCF or relaxation did not converge | see `problems` in the report |
| `converged` | all checks passed | usable by later stages and the analysis |

Open `results/INDEX.md` (it links every `report.html`) for an overview; open a run's
`report.html` for its inputs, checks, energies and event history. Layout and file formats are
described in [Data Model](data_model.md).

## Common situations

| Situation | Fix |
|---|---|
| Job ran out of walltime | Increase `hpc.walltime` in the campaign, `plan`, `prepare` (resources are not physics, so the run id stays), then `run --mode submit --resubmit` (the previous `raw/` is archived under `attempts/`). |
| SCF not converged | Raise `NELM` or change `ALGO` in the campaign `vasp.incar`; this changes the physics hash, so also set a new `tag:`. |
| Relaxation hit NSW | Raise `NSW` (new `tag:`), or restart from CONTCAR with a `builder: file` run. |
| `already submitted` but the job died before VASP started | `run --mode submit --resubmit`. |
| You need to change physics of finished runs | Never overwrite: set `tag: v2` in the campaign; new run ids are `..._v2`, and `analyze solubility --tag v2` prefers them. |
| `parent run ... must be converged` | Finish and `collect` the parent stage first. |
| Smoke fails: VASP binary not found | Fix `environment.modules` in `configs/site.yaml` (see [HPC Setup](hpc_setup.md)); smoke again. |

## Rules that keep results defensible

1. Never edit files inside `results/runs/<run_id>/inputs` or `configs/generated/` by hand.
2. Never change `common_settings.yaml` or `converged_settings.yaml` without re-running every stage that depends on them (use a new `tag`).
3. Commit campaign files and results (manifests, metrics, reports, inputs except POTCAR) together; see [Data Model](data_model.md#what-to-commit).
4. Record decisions (chosen settings, discarded runs, surprises) in `progress/`.
