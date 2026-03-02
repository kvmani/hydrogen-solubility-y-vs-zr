# Presentation Tooling

## Purpose
Generate standardized lab-meeting decks from repository artifacts using the project slide style contract.

## Style Contract
- Arial font throughout
- Black title bar with white 24 pt title text
- Body split: left 20% bullets, right 80% primary visual
- Black bottom bar with white 20 pt bottom-line statement
- Slide flow: objective -> methodology -> equations/setup -> results -> conclusions

## Scripts
- `draft_manifest.py`: scans artifacts and drafts a manifest JSON.
- `build_ppt_from_manifest.py`: renders `.pptx` from manifest using style contract.
- `generate_lab_meeting_ppt.py`: one-command workflow that writes:
  - `<basename>_manifest.json`
  - `<basename>.pptx`
  - `<basename>.pdf` (via LibreOffice `soffice`, when available)

## Example
```bash
python tools/presentation/generate_lab_meeting_ppt.py \
  --scan-root results \
  --output-dir presentations \
  --deck-title "Y vs Zr Hydrogen Solubility - Stage Update" \
  --basename y-zr-stage-update \
  --max-results 10 \
  --require-pdf
```
