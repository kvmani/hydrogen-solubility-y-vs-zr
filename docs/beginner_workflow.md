# Beginner Workflow For This Project

This page is the practical guide for newcomers. It explains what to run, what files matter, and how to read the results without needing to know the whole codebase first.

## What The Workflow Is Trying To Do

The project compares hydrogen in Y and Zr by moving through three layers:

1. a clean DFT setup for the host metals,
2. dilute hydrogen insertion calculations,
3. thermodynamic interpretation of the resulting energies.

The goal of the workflow is not just to run calculations. It is to produce evidence that can be defended later.

## The Four Questions Every Run Must Answer

For each run, ask:

1. What was the calculation trying to measure?
2. What inputs were used?
3. Did the run converge?
4. What is the result supposed to mean scientifically?

If you cannot answer all four, the run is not ready for project decisions.

## Main Inputs

The important VASP inputs are:

- `POSCAR`: the structure and atomic positions,
- `POTCAR`: the pseudopotentials,
- `KPOINTS`: the reciprocal-space sampling,
- `INCAR`: the run controls.

For this project, the matching config file is just as important as the VASP files. It is the source of truth for:

- run identity,
- host system,
- cutoff,
- k-mesh,
- convergence scan,
- scheduler metadata,
- provenance labels.

## Main Outputs

The run directory should contain:

- `inputs/config_snapshot.*`: the exact config used,
- `manifest.json`: provenance and execution history,
- `metrics.json`: parsed numerical results,
- `report.html`: quick human-readable summary,
- `logs/`: orchestration and scheduler logs,
- `raw/`: raw VASP outputs,
- `parsed/`: derived tables or summaries.

The project treats the run directory as a complete scientific record.

## Recommended Execution Order

Use this order every time:

1. Validate the config.
2. Initialize the run directory.
3. Run `dryrun`.
4. Run `smoke`.
5. Run `submit`.
6. Parse outputs.
7. Review the HTML report.

That order prevents wasted queue time and keeps failures easy to diagnose.

## Step 1: Validate The Config

Command:

```bash
python tools/validate_config.py configs/stage1_y_host_validation_v1.yaml
```

What this checks:

- config syntax,
- run ID structure,
- system/stage consistency,
- convergence scan definitions,
- scheduler fields,
- provenance labels.

Why it matters:

If the config is wrong, everything downstream is suspect.

## Step 2: Initialize The Run Directory

Command:

```bash
python tools/init_run.py configs/stage1_y_host_validation_v1.yaml
```

What this creates:

- the `results/runs/<run_id>/` folder,
- subfolders for inputs, logs, raw outputs, and parsed data,
- starter `manifest.json`,
- starter `metrics.json`,
- starter `report.html`.

What to check:

- the run ID is correct,
- the config snapshot was copied,
- the manifest and metrics were created,
- the path matches the config.

## Step 3: Stage The Input Decks

Before running, make sure the run directory has the VASP files:

- `POSCAR`
- `KPOINTS`
- `INCAR`
- `POTCAR`

Beginner checklist:

- `POSCAR` species order must match `POTCAR`.
- The structure should match the intended system and phase.
- The numerical settings should match the validated config.

## Step 4: Dry Run

The dry run checks whether the workflow is structurally ready.

It does not consume real compute time. It checks:

- config validity,
- run directory state,
- input completeness,
- scheduler script generation.

This is the first gate.

## Step 5: Smoke Run

The smoke run checks whether the environment and launcher are actually healthy.

It is the best way to catch:

- module issues,
- launcher syntax issues,
- missing runtime dependencies,
- scheduler environment problems.

This is the second gate.

## Step 6: Submit

Only submit after dry run and smoke run have passed.

Why this matters:

- it prevents avoidable compute waste,
- it keeps failures interpretable,
- it protects the comparison between Y and Zr from inconsistent setup errors.

## Step 7: Parse Outputs

Command:

```bash
python tools/extract_metrics.py --run-dir results/runs/<run_id>
```

This reads `OUTCAR` and `OSZICAR`, then writes `metrics.json` and refreshes `report.html`.

What the parser tries to infer:

- total energy,
- energy per atom,
- whether electronic convergence was achieved,
- whether ionic convergence was achieved,
- whether the run is `success`, `partial`, or `failed`.

## How To Read `metrics.json`

Think of `metrics.json` as the machine-readable summary.

Important fields:

- `status`: the overall run state,
- `energetics.total_energy_eV`: the best recovered total energy,
- `energetics.energy_per_atom_eV`: useful for host comparisons,
- `checks.electronic_converged`: whether SCF convergence was reached,
- `checks.ionic_converged`: whether geometry optimization converged,
- `artifacts`: paths back to raw evidence.

If `total_energy_eV` is missing, the run is not yet useful for science.

If the status is `partial`, some information was recovered but the result should be treated cautiously.

## How To Read `report.html`

The report is the human-facing mirror of the machine-readable files.

Use it to answer:

- what system was run,
- what the objective was,
- what energy was recovered,
- which checks passed,
- what the next action is.

This is the fastest way to inspect a run without opening every raw file.

## How To Infer Scientific Results

For Stage-1 host validation, you are looking for numerical stability:

- energies should stop changing materially as `ENCUT` increases,
- energies should stop changing materially as k-point density increases,
- Y and Zr should be compared with the same method settings.

For later hydrogen runs, you will look for:

- which interstitial site is lowest in energy,
- how large the solution energy is,
- whether corrections change the ranking,
- whether hydride formation becomes preferable.

## Beginner Interpretation Rules

Do not jump straight from one energy to a solubility conclusion.

Instead:

1. check convergence,
2. confirm the setup is comparable,
3. inspect the energetic trend,
4. apply the thermodynamic model,
5. compare against literature anchors.

That sequence avoids the most common beginner mistake: treating a single DFT total energy as the final answer.

## Practical Short Workflow

If you want the shortest correct path:

1. Read `docs/dft_introduction.md`.
2. Validate the config.
3. Run `init_run`.
4. Run `dryrun`.
5. Run `smoke`.
6. Submit.
7. Parse outputs.
8. Read the report.

## Where To Go Next

- For theory, read [`docs/dft_introduction.md`](dft_introduction.md).
- For project science, read [`docs/scientific_foundation.md`](scientific_foundation.md).
- For the VASP basics, read [`docs/vasp_primer.md`](vasp_primer.md).
- For the full host workflow, read [`docs/vasp_simulation_guide.md`](vasp_simulation_guide.md).

