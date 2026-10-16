# 2026-10-16: End-to-end workflow refactor (`hsol`)

## Why

A review of the Stage-1 tooling found problems that would have invalidated results or blocked a
beginner:

- **ENCUT sweep was silently wrong.** `run_vasp_pipeline.sh` copied a fixed INCAR template
  (ENCUT = 520) into every run, so the committed dry-run for the "ENCUT 400" config carried
  ENCUT = 520. The config values never reached VASP.
- POSCAR, KPOINTS and POTCAR were never generated; every run needed hand-made inputs.
- The Stage-1 configs combined a 96-atom 4×4×3 supercell with a 12×12×8 k-mesh and ISIF=3
  relaxation for convergence tests: very expensive, and mixing basis/k-point errors with Pulay
  stress.
- The parser reported SCF convergence whenever any energy was printed; unfinished relaxations of
  static-looking runs could pass.
- Partition/account placeholders had to be patched into every generated config.
- Nothing existed beyond Stage 1 (no H, vibration, hydride or solubility tooling).

## Decisions

- One CLI, `./hsol` (plan / prepare / run / collect / status / analyze / doctor), replacing 11
  scripts. The Slurm pipeline is now Python and tested.
- Campaign files per stage are the single source of physics; run configs (schema 2.0) are
  generated and fully explicit. Shared physics lives in `common_settings.yaml`; converged ENCUT and
  k-point spacing in `converged_settings.yaml`.
- Convergence on the 2-atom primitive cell with static runs; k-points swept and reused as a
  *spacing* (KSPACING convention) so the converged density transfers to every cell.
- Cluster settings moved to `configs/site.yaml` (not in git).
- Descriptive run ids (`Y_stage2_hT`) instead of date + sequence numbers; changed physics gets a
  `tag` suffix and never overwrites results.
- `submit` requires a passing smoke test for exactly the current inputs and site settings.
- Model for Stage 5: ideal lattice gas on hcp T/O sites, harmonic H vibrations (metal fixed),
  ideal-gas H₂, fluorite MH₂ hydride; TSS from the coexistence condition (see `docs/scheme.md`).
- Removed: the March 2026 dry-run artifacts and generated campaign (never computed, wrong INCARs),
  the INCAR/sbatch templates, committed presentation binaries, and docs superseded by
  `workflow.md`, `hpc_setup.md`, `scheme.md` and `data_model.md`. All remain in git history.

## Validation

- 55 pytest tests: site geometry, POSCAR I/O, k-spacing rule, config/campaign validation, parser
  edge cases, H₂ gas model vs NIST entropies (< 0.5 %), and end-to-end plan → prepare → dryrun →
  smoke → submit (fake Slurm/VASP) → collect → both analyses with hand-checked numbers.
- Passes on Python 3.9 and 3.13; ruff clean; `sphinx -W` build clean.

## Open

1. Run Stage 1a on the cluster; fill in `converged_settings.yaml`.
2. Enter experimental TSS points; add a benchmark overlay to the solubility analysis.
3. Supercell-size check for Stage 2 (4×4×3 with `tag`).
4. Zr hydride model choice (fluorite vs ε-ZrH₂ vs ordered δ-ZrH₁.₅).
