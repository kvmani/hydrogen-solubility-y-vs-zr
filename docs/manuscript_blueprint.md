# Manuscript Blueprint

This page is the bridge between the technical documentation and the eventual scientific manuscript.

## Manuscript Thesis

The paper should argue, with quantitative evidence, that the hydrogen solubility contrast between yttrium and zirconium arises from a combination of:

1. host-specific insertion energetics,
2. finite-temperature vibrational corrections,
3. configurational entropy,
4. hydride competition and phase stability.

That is the core claim tree. Everything else in the project exists to support it.

## Proposed Section Structure

### 1. Introduction

- State the experimental contrast.
- Summarize why the contrast matters physically and technologically.
- Frame the question as a free-energy problem, not a static-energy problem.

### 2. Background And Literature Context

- Summarize the historical Y-H and Zr-H phase assessments.
- Identify the gap: no single, fully reproducible first-principles-to-solubility chain with shared methodology.
- Position the project as a comparative study rather than a host-specific calculation exercise.

### 3. Computational Methods

- Host structures and reference states.
- DFT functional and PAW formalism.
- Supercell and k-point convergence logic.
- Vibrational correction workflow.
- Data handling, provenance, and run-directory layout.

### 4. Host Validation Results

- Alpha-Y and alpha-Zr convergence tables.
- Total-energy and energy-per-atom benchmarks.
- Geometry relaxation sanity checks.

### 5. Dilute Hydrogen Energetics

- Site-resolved insertion energies.
- Tetrahedral versus octahedral preference.
- Sensitivity to supercell size, k-mesh, and ENCUT.

### 6. Finite-Temperature Corrections

- Vibrational free energies.
- Zero-point energy shifts.
- Which corrections move the Y-vs-Zr contrast and which cancel.

### 7. Hydride Competition And Solubility

- Hydride formation free energies.
- Dilute-to-hydride crossover conditions.
- Predicted $c_H(T, p)$ curves and uncertainty bounds.

### 8. Discussion

- Mechanistic interpretation.
- Comparison to literature anchors.
- Limitations of the model and where further work is needed.

### 9. Conclusion

- State the final explanatory mechanism in one paragraph.
- Identify the strongest quantitative result.
- Note the remaining uncertainty explicitly.

## Claim-To-Evidence Map

| Claim | Evidence to produce | Primary documentation source |
| --- | --- | --- |
| Y stores more H than Zr in the dilute regime | literature anchors + computed site free energies | `literature/lit_review.md`, `docs/scientific_foundation.md` |
| Static DFT is not enough | vibrational corrections and finite-T free energies | `docs/scientific_foundation.md` |
| Zr hydride competition truncates the dilute regime | hydride free-energy comparisons | `docs/scientific_foundation.md`, `docs/roadmap.md` |
| The workflow is reproducible | run manifests, metrics, and HTML reports | `docs/provenance_and_contract.md` |

## Figure And Table Plan

The paper should eventually include at least:

- a workflow schematic,
- a free-energy decomposition figure,
- a TSS/T comparison plot for Y and Zr,
- a site-preference energy table,
- a convergence summary table,
- a provenance summary table.

## Writing Rule

Do not write the manuscript as a narrative first and then backfill evidence.

Write the evidence map first, then convert the evidence map into the paper outline, and only then draft prose.

## References

```{bibliography}
```
