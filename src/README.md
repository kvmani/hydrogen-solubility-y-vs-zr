# src/hydrogen_solubility

The Python package behind `./hsol`. Module roles are listed in
[`docs/api_reference.md`](../docs/api_reference.md); tests live in `tests/`.

Design rules: no scientific defaults hidden in code (all physics comes from campaign files),
standard library + pyyaml + pydantic only (matplotlib optional), Python >= 3.9 so it runs on
HPC login nodes, and every user-facing failure explains how to fix it.
