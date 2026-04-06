# presentations/

## Purpose
Store presentation assets derived from documented results.

## Goes In
- Slide deck source notes and figure references used for talks/reviews
- Deck generation manifests and scratch notes while working locally

## Does NOT Go In
- Primary raw simulation data
- Untraceable screenshots without run context
- Generated `.pptx` and `.pdf` deck binaries, which are treated as build artifacts and ignored by git

## Mission Link
Communicates validated findings while preserving traceability to reproducible runs.

## Required For Major Updates
Every major result set or feature addition should still be turned into a `.pptx`/`.pdf` deck for review, but the rendered files remain untracked.

## Generator
Use:
- `python tools/presentation/generate_lab_meeting_ppt.py --scan-root results --output-dir presentations --deck-title \"<title>\" --require-pdf`

Style is enforced by script (Arial fonts, black title/footer bars, 20/80 content split).
