# Roadmap With Stage Gates

## Stage 0: Literature Baseline And Hypothesis Framing
- Objective: establish credible evidence map and initial hypotheses.
- Outputs: curated `literature/lit_review.md`, `library.bib`, gap list, testable hypotheses.
- Gate to Stage 1:
  - Y-H and Zr-H solubility/phase references captured with DOI-backed provenance.
  - Initial quantitative targets defined (temperature range, composition ranges).

## Stage 1: Baseline DFT Validation (Pure Hosts)
- Objective: validate computational setup for alpha-Y and alpha-Zr hosts.
- Outputs: converged host energies/volumes, k-point and ENCUT convergence records.
- Gate to Stage 2:
  - Convergence thresholds documented and met.
  - Manifest + metrics emitted for all validation runs.

## Stage 2: H Interstitial Energetics
- Objective: compute dilute-H solution energies and site preference (T/O and any symmetry-distinct sites).
- Outputs: site-resolved energies, relaxed structures, uncertainty/sensitivity table.
- Gate to Stage 3:
  - Stable site hierarchy established for both Y and Zr.
  - Cross-check against literature trends completed.

## Stage 3: Vibrational And ZPE Corrections
- Objective: add finite-temperature free-energy corrections relevant to H.
- Outputs: phonon/ZPE contributions for key host+H states.
- Gate to Stage 4:
  - Free-energy correction protocol validated and reproducible.
  - Correction magnitudes sanity-checked vs literature ranges.

## Stage 4: Hydride Competition And Phase Stability
- Objective: include competing hydride phases in thermodynamic picture.
- Outputs: hydride formation free energies and stability windows.
- Gate to Stage 5:
  - Explicit criterion for precipitation vs dilute dissolution established.
  - Y and Zr treated under consistent reference framework.

## Stage 5: Solubility Model Construction
- Objective: translate first-principles energetics to c_H(T,p) predictions.
- Outputs: calibrated model, uncertainty bars, comparison to experimental/TSS data.
- Gate to Stage 6:
  - Model reproduces key contrast trend (high Y, low Zr) with defensible assumptions.
  - Residual discrepancy analysis documented.

## Stage 6: Manuscript Package
- Objective: produce publication-ready narrative and artifacts.
- Outputs: figures, tables, methods appendix, reproducibility checklist.
- Completion criteria:
  - End-to-end rerunability from configs and docs.
  - Claim-to-evidence mapping complete and citation-checked.
