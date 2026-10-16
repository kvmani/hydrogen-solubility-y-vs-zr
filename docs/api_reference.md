# API Reference

The command line (`hsol`, module `hydrogen_solubility.cli`) is a thin layer over these modules,
which can also be imported in notebooks and tests.

| Module | Role |
|---|---|
| `config_models` | run-config and site-config schemas, loading and validation |
| `planner` | campaign file → run configs (`hsol plan`) |
| `structures` | hcp, interstitial, H₂ and fluorite builders; POSCAR I/O; k-point spacing |
| `vasp_inputs` | INCAR/KPOINTS writers, POTCAR assembly and identity |
| `run_bootstrap` | run directories, inputs and manifest (`hsol prepare`) |
| `pipeline` | dryrun → smoke → submit on Slurm (`hsol run`) |
| `vasp_metrics` | OUTCAR/OSZICAR parsing and convergence assessment |
| `results_index` | `hsol collect`, `hsol status`, run lookup |
| `convergence` | Stage-1a analysis |
| `thermo` | harmonic free energies, ideal-gas H₂, lattice-gas occupancies |
| `solubility` | Stage-5 model (`hsol analyze solubility`) |
| `provenance`, `reporting`, `paths` | hashes and events, `report.html`, repository locations |

```{eval-rst}
.. autosummary::
   :toctree: _autosummary

   hydrogen_solubility.config_models
   hydrogen_solubility.planner
   hydrogen_solubility.structures
   hydrogen_solubility.vasp_inputs
   hydrogen_solubility.run_bootstrap
   hydrogen_solubility.pipeline
   hydrogen_solubility.vasp_metrics
   hydrogen_solubility.results_index
   hydrogen_solubility.convergence
   hydrogen_solubility.thermo
   hydrogen_solubility.solubility
   hydrogen_solubility.provenance
   hydrogen_solubility.reporting
   hydrogen_solubility.paths
   hydrogen_solubility.cli
```
