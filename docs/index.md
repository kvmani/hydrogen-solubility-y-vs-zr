# Hydrogen Solubility in α-Y vs α-Zr

A reproducible DFT (VASP) + thermodynamics workflow that explains why hydrogen is far more soluble
in yttrium than in zirconium. One command, `./hsol`, takes you from campaign files to Slurm jobs,
parsed results and the final solubility model, recording provenance at every step.

## Where to start

| You want to… | Read |
|---|---|
| run calculations | [HPC Setup](hpc_setup.md) once, then [Workflow](workflow.md) |
| understand the science and what each calculation is for | [Scheme](scheme.md), then [Scientific Foundation](scientific_foundation.md) |
| know what is done and what is next | [Roadmap](roadmap.md) |
| look up a config key or a file format | [Configuration Reference](config_schema.md), [Data Model](data_model.md) |
| learn DFT/VASP basics first | [DFT Introduction](dft_introduction.md), [VASP Primer](vasp_primer.md) |

```{toctree}
:caption: Use
:maxdepth: 2

workflow
hpc_setup
roadmap
```

```{toctree}
:caption: Science
:maxdepth: 2

scheme
scientific_foundation
dft_introduction
vasp_primer
literature_map
manuscript_blueprint
```

```{toctree}
:caption: Reference
:maxdepth: 2

config_schema
data_model
api_reference
mission
collaboration_contract
```

## Build these docs

```bash
pip install -r requirements-docs.txt
make docs          # = python -m sphinx -W -b html docs docs/_build/html
```
