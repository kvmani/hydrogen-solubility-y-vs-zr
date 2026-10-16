# Data Model and Provenance

Every calculation is one **run**: one directory, one id, one complete record.

## Naming

- **run_id** = `<system>_<stage>_<label>[_<tag>]`, e.g. `Y_stage2_hT`, `Zr_stage1_kspacing0.13`,
  `H2_stage3_vib_molecule`, `Y_stage2_hT_v2`. The label comes from the campaign file; the optional
  tag marks a re-run with changed physics. Ids are never reused for different physics.
- **system**: `Y`, `Zr` or `H2` (gas reference). **stage**: `stage1` … `stage6` (see [Roadmap](roadmap.md)).

## Repository layout

```text
configs/campaigns/        campaign files (the scientific source of truth, committed)
configs/generated/        run configs written by `hsol plan` (derived, not committed)
configs/site.yaml         cluster settings (personal, not committed)
results/runs/<run_id>/    one directory per run (see below)
results/INDEX.md          overview of all runs with links to reports  (hsol status)
results/index.csv         same, machine-readable
results/analysis/         convergence/ and solubility/ outputs           (hsol analyze)
results/batch_logs/       per-invocation summaries of `hsol run`        (not committed)
```

## Run directory

```text
results/runs/<run_id>/
  inputs/config.yaml      exact config used (snapshot)
  inputs/INCAR KPOINTS POSCAR POTCAR
  raw/                    VASP working directory: OUTCAR, OSZICAR, CONTCAR, vasp.out, ...
  logs/<UTC>_<mode>/      pipeline.log, job.sbatch, smoke/sbatch logs of each invocation
  logs/slurm-<job>.out|err
  attempts/<UTC>/         previous raw/ directories archived by --resubmit
  manifest.json           provenance and event history
  metrics.json            parsed results and checks
  report.html             human-readable summary of the above
```

## `manifest.json`

Written by `prepare`, then only appended to.

| Field | Content |
|---|---|
| `run_id`, `stage`, `system`, `calc_type`, `campaign`, `objective`, `sweep` | identity |
| `config` | source path of the config and `sha256` of its physics-relevant part |
| `inputs` | SHA-256 of INCAR/KPOINTS/POSCAR/POTCAR and their combined `input_hash` |
| `potcars` | per element: label, TITEL, ENMAX, SHA-256, source path |
| `structure` | builder, composition, lattice, supercell, H site, k-grid and spacing, parent runs (with CONTCAR hashes) |
| `git` | commit, branch, dirty flag at prepare time |
| `environment` | workflow version, Python, host, platform |
| `vasp.version` | from OUTCAR, filled in by `collect` |
| `hpc` | nodes, ntasks, walltime, partition, account, modules, `job_id` |
| `events` | list of `{timestamp_utc, event, status, mode, message, details}` |

Events: `prepared`, `inputs_regenerated`, `config_snapshot_updated`, `prepare_warnings`,
`dryrun_completed`, `smoke_completed`, `submitted`, `resubmit_archived`, `<mode>_failed`,
`collected`. A smoke event stores the `input_hash` and site fingerprint it validated; `submit`
refuses unless they match the current ones.

## `metrics.json`

Written by `prepare` (status only) and `collect`.

| Field | Content |
|---|---|
| `status` | `prepared`, `submitted`, `not_started`, `incomplete`, `unconverged`, `converged` |
| `problems` | reasons the run is not `converged` |
| `warnings` | physics flags that do not fail the run (H left its site, imaginary modes) |
| `checks` | `completed_normally`, `electronic_converged`, `ionic_converged` (relaxations), `vibrations_parsed` (finite differences); `null` = not applicable |
| `energetics` | `energy_sigma0_eV` (headline energy), `free_energy_eV` (TOTEN), `energy_per_atom_eV` |
| `calculation` | VASP version, NIONS, ionic steps, SCF steps of the last ionic step, NELM, max force, pressure, elapsed time |
| `structure_check` | from CONTCAR: volume/atom; `a_A`, `c_A`, `c_over_a` (host relax); `requested_site`, `final_site`, `site_preserved` (H interstitial); cell lengths (hydride) |
| `vibrations` | `n_modes`, `n_imaginary`, `modes` (meV, cm⁻¹, imaginary flag) |

Convergence is judged from evidence: VASP's final timing block must exist; the last ionic step must
finish its SCF in fewer than NELM steps; relaxations must report "reached required accuracy".

## What to commit

Commit campaign files together with the results they produced: `manifest.json`, `metrics.json`,
`report.html`, `inputs/` (POTCAR is ignored automatically), `raw/OUTCAR`, `OSZICAR`, `CONTCAR`,
`vasp.out`, `logs/`, plus `results/INDEX.md`, `results/index.csv` and `results/analysis/`.
`.gitignore` excludes POTCAR (licence) and large regenerable files (WAVECAR, CHGCAR, CHG,
vasprun.xml, PROCAR, DOSCAR, LOCPOT, ELFCAR). If OUTCARs become too large for git, archive them
next to the clone and keep their SHA-256 in a progress note.

## Analysis outputs

| Path | Content |
|---|---|
| `results/analysis/convergence/summary.md` | ENCUT and k-spacing tables, recommended settings (paste into `converged_settings.yaml`) |
| `results/analysis/convergence/convergence_table.csv`, `encut.png`, `kpoints.png` | data and plots |
| `results/analysis/solubility/summary.md` | site energetics, ZPE, ΔG(T), solubility-limit gap, TSS ratio, runs used, missing inputs, assumptions |
| `results/analysis/solubility/site_energetics.csv` | per system and site: static ΔE, ΔZPE, ΔG at 300/600/900 K |
| `results/analysis/solubility/solubility_vs_T.csv`, `solubility.png` | x_H(T) at the requested pressures, TSS (H/M and wppm), plateau pressure |
