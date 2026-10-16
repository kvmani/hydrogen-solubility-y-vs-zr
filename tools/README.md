# tools/

The workflow itself is `./hsol` (see [`docs/workflow.md`](../docs/workflow.md)). This folder holds
helpers that are not part of the run loop:

| Script | Use |
|---|---|
| `hpc/discover_vasp_modules.sh` | find VASP modules and binaries on a new cluster |
| `hpc/check_vasp_installation.sh` | verify a module stack, optionally with a one-atom VASP run |
| `presentation/` | build lab-meeting decks (`.pptx`/`.pdf`) from results; needs `pip install -r requirements-dev.txt` |

Both HPC scripts print `--help`; their use is described in [`docs/hpc_setup.md`](../docs/hpc_setup.md).
