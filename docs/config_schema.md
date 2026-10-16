# Configuration Reference

Three kinds of YAML file, from most to least often edited:

| File | Edited by | Purpose |
|---|---|---|
| `configs/campaigns/*.yaml` | you | describe one stage for all systems |
| `configs/site.yaml` | you, once per cluster | Slurm, modules, launcher, POTCAR library ([HPC Setup](hpc_setup.md)) |
| `configs/generated/<campaign>/<run_id>.yaml` | `hsol plan` only | one fully explicit run config (schema below) |

Unknown keys are errors everywhere, so typos never pass silently.

## Campaign files

```yaml
campaign: stage2_h_energetics       # output folder name and run metadata
stage: stage2                       # part of every run_id
tag: v2                             # optional: appended to run_ids for a re-run with changed physics
include: [common_settings.yaml, converged_settings.yaml]   # merged first (only `defaults` inside)
defaults:   {structure: ..., vasp: ..., potcars: ..., hpc: ..., notes: [...]}
systems:    {Y: {...}, Zr: {...}}   # per-system overrides
runs:                               # created once per system (restrict with `systems: [Y]`)
  - {label: hT, calc_type: h_interstitial, objective: "...{system}...", structure: {h_site: tetrahedral}}
shared_runs:                        # created once, explicit system
  - {label: molecule, system: H2, calc_type: h2_reference, ...}
sweeps: {calc_type: host_convergence, encut_eV: [...], kpoint_spacing: [...]}   # stage 1a helper
```

Merge order: included defaults → `defaults` → `systems.<X>` → run entry. Mappings merge key by
key; lists are replaced; `null` clears an inherited value (e.g. `kpoints: {grid: [1,1,1], spacing: null}`).
`{system}` in any string becomes the system name. Strings written as `"<...>"` are placeholders
that block planning until filled in.

Shared files: `common_settings.yaml` (PREC, smearing, LASPH, LREAL, ISPIN, POTCAR labels — identical
for every calculation) and `converged_settings.yaml` (ENCUT and k-point spacing from Stage 1a).

## Run config (`schema_version: "2.0"`)

### `run`

| Key | Meaning |
|---|---|
| `run_id` | must start with `<system>_<stage>_` |
| `stage` | `stage1` … `stage6` |
| `system` | `Y`, `Zr`, `H2` |
| `calc_type` | see table below |
| `objective` | one sentence, ≥ 12 characters |
| `campaign`, `sweep`, `notes` | set by the planner |

| `calc_type` | allowed `structure.builder` | typical INCAR |
|---|---|---|
| `host_convergence` | `hcp_primitive`, `file` | static (IBRION −1, NSW 0) |
| `host_relax` | `hcp_primitive`, `file` | IBRION 2, ISIF 3, positive EDIFFG |
| `host_supercell` | `hcp_supercell`, `file` | static |
| `h_interstitial` | `hcp_supercell` (+ `h_site`), `file` | IBRION 2, ISIF 2, EDIFFG −0.01 |
| `h2_reference` | `h2_molecule`, `file` | ISMEAR 0, SIGMA 0.01, Γ only |
| `hydride_relax` | `fluorite_dihydride`, `file` | IBRION 2, ISIF 3, positive EDIFFG |
| `vibration` | `from_run` | IBRION 5, POTIM 0.015, NFREE 2 |

### `structure`

| Key | Used by | Meaning |
|---|---|---|
| `builder` | all | how POSCAR is made |
| `source` | all | provenance text (where the geometry comes from) |
| `a_A`, `c_A` | `hcp_*` | lattice parameters in Å … |
| `lattice_from_run` | `hcp_*` | … or take a, c from this converged run's CONTCAR (exactly one of the two) |
| `supercell` | `hcp_supercell` | repeats, e.g. `[3, 3, 2]` |
| `h_site` | `h_interstitial` | `tetrahedral` or `octahedral` |
| `box_A`, `bond_A` | `h2_molecule` | vacuum box (Å, use three different lengths) and initial bond length |
| `a_A` | `fluorite_dihydride` | cubic lattice parameter (starting value) |
| `from_run`, `free_species` | `from_run` | parent run whose CONTCAR is used; species allowed to move (selective dynamics) |
| `file` | `file` | path to a POSCAR (VASP 5 format with species line) |

### `vasp`

| Key | Meaning |
|---|---|
| `incar` | literal INCAR tags (upper case). Required: ENCUT, PREC, EDIFF, ISMEAR, SIGMA, IBRION, NSW. `SYSTEM` is written automatically. |
| `kpoints.grid` **or** `kpoints.spacing` | explicit mesh, or spacing in Å⁻¹ incl. 2π (VASP KSPACING convention), converted per cell by `prepare` |
| `kpoints.style` | `Gamma` (default; keeps hexagonal symmetry) or `Monkhorst-Pack` |
| `binary` | `std` (default) or `gam` (needs a 1×1×1 Γ grid; uses `vasp.binary_gam` from the site config) |

### `potcars` and `hpc`

`potcars` maps each element to a PAW label (`Y: Y_sv`, `Zr: Zr_sv`, `H: H`); every species in the
POSCAR needs one. `hpc` holds `nodes`, `ntasks` and `walltime` (`HH:MM:SS` or `D-HH:MM:SS`).
Resources are not part of the physics hash, so changing them never forces a new run id.

## Validation

`./hsol validate <files or dirs>` checks run configs; `plan` validates everything it generates
before writing; `prepare` additionally checks POTCAR identities (TITEL element, PAW_PBE) and warns
when ENCUT is below ENMAX, or below 1.3 × ENMAX for cell relaxations.
