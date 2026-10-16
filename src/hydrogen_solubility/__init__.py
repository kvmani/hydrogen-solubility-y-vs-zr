"""Reproducible DFT workflow for comparing hydrogen solubility in alpha-Y and alpha-Zr.

The command-line entry point is ``hsol`` (see ``hydrogen_solubility.cli``); the
modules below are importable for notebooks and tests.

* ``config_models`` -- run/site configuration schemas
* ``structures``    -- hcp, interstitial, H2 and hydride POSCAR builders
* ``vasp_inputs``   -- INCAR/KPOINTS/POTCAR writers
* ``vasp_metrics``  -- OUTCAR/OSZICAR parsers and ``metrics.json`` payloads
* ``run_bootstrap`` -- ``hsol prepare``: run directories, inputs, provenance
* ``pipeline``      -- ``hsol run``: dryrun -> smoke -> submit on Slurm
* ``results_index`` -- ``hsol collect`` / ``hsol status``
* ``planner``       -- ``hsol plan``: campaign file -> run configs
* ``convergence``, ``thermo``, ``solubility`` -- analysis
"""

from .__version__ import __version__

__all__ = ["__version__"]
