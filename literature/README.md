# literature/

## Purpose
Maintain a traceable, high-quality literature evidence base for Y-H and Zr-H science and method choices.

## Goes In
- `library.bib`: canonical BibTeX entries (DOI-first)
- `lit_review.md`: annotated evidence map and gap tracking
- `benchmarks/`: machine-readable target extractions and provenance maps
- DOI links, provenance notes, and tags

## Does NOT Go In
- Unverifiable claims without source information
- Citation dumps without annotations
- Paywalled PDFs committed to git (store metadata/notes instead)

## Mission Link
The literature set defines factual constraints and validates model assumptions for the Y vs Zr solubility explanation.

## Workflow
1. Add source metadata with DOI to `library.bib`.
2. Add a concise annotation (2-5 lines) in `lit_review.md`.
3. Tag each source (experiment, phase-diagram, DFT, phonon, thermodynamics).
4. Record provenance: where data are extracted from (figure/table/equation).
5. Mark confidence and any unresolved conflicts between sources.
6. Promote extracted quantitative targets into `benchmarks/tss_benchmark_records.csv`.
