# Hydrogen solubility in α-Y vs α-Zr from first principles

Why does yttrium dissolve far more hydrogen than zirconium? This repository answers that with a
reproducible chain of VASP calculations and a thermodynamic model: host convergence → relaxed
lattices → H in tetrahedral/octahedral sites → zero-point and vibrational free energies →
hydride competition → solubility limit (TSS) for both metals with identical settings.

One command, `./hsol`, prepares every input, runs Slurm jobs safely (dryrun → smoke → submit),
collects results with full provenance and performs the analysis.

## Quick start

```bash
pip install -r requirements.txt                    # Python >= 3.9: pyyaml, pydantic, matplotlib
cp configs/site.example.yaml configs/site.yaml     # cluster settings: partition, account, modules, POTCARs
./hsol doctor                                      # lists anything still missing

./hsol plan    configs/campaigns/stage1_convergence.yaml
./hsol prepare configs/generated/stage1_convergence
./hsol run --mode dryrun configs/generated/stage1_convergence
./hsol run --mode smoke  configs/generated/stage1_convergence
./hsol run --mode submit configs/generated/stage1_convergence
./hsol status                                      # progress board; also writes results/INDEX.md
./hsol analyze convergence                         # -> paste result into configs/campaigns/converged_settings.yaml
```

Then repeat plan → prepare → run for `stage1_relax`, `stage2_h_energetics`, `stage3_vibrations`,
`stage4_hydrides`, `stage4_hydride_vibrations`, and finish with `./hsol analyze solubility`.

## Documentation

| Document | Use it for |
|---|---|
| [docs/workflow.md](docs/workflow.md) | **the commands**, stage by stage, statuses, troubleshooting |
| [docs/hpc_setup.md](docs/hpc_setup.md) | one-time cluster setup (modules, POTCARs, `site.yaml`) |
| [docs/scheme.md](docs/scheme.md) | **the science**: which calculation feeds which equation, assumptions |
| [docs/roadmap.md](docs/roadmap.md) | stages, gates, open items |
| [docs/config_schema.md](docs/config_schema.md), [docs/data_model.md](docs/data_model.md) | config keys; run directories, manifests, metrics |
| [docs/dft_introduction.md](docs/dft_introduction.md), [docs/vasp_primer.md](docs/vasp_primer.md) | DFT/VASP background for beginners |
| [mission_goals.md](mission_goals.md), [agents.md](agents.md) | scope and collaboration rules |

The same pages form a Sphinx site: `pip install -r requirements-docs.txt && make docs`.

## Repository layout

```text
hsol                    command-line entry point (./hsol --help)
configs/campaigns/      what to compute, one file per stage (edit these)
configs/site.yaml       your cluster settings (from site.example.yaml; not in git)
src/hydrogen_solubility/  the Python package behind hsol
results/runs/<run_id>/  one directory per calculation: inputs, raw outputs, manifest, metrics, report
results/INDEX.md        overview of all runs with links to their reports
results/analysis/       convergence and solubility results
literature/             bibliography, annotated review, experimental benchmarks
tools/hpc/              VASP module discovery and installation check
tools/presentation/     lab-meeting slide generator
progress/               dated decision records
tests/                  pytest suite (make check)
```

## Guarantees the workflow gives you

- Every INCAR/KPOINTS/POSCAR is generated from a reviewed campaign file; nothing is hand-edited.
- Y and Zr share one set of physics settings (`configs/campaigns/common_settings.yaml`).
- Nothing is submitted unless a smoke test passed for exactly the current inputs and cluster settings.
- Results are never overwritten: changed physics requires a new run id.
- Each run records git commit, input hashes, POTCAR identities, VASP version, job ids and an event
  history, and gets a human-readable `report.html`.

## Development

`make check` runs lint, the test suite and a strict docs build (also run by CI on every push).
