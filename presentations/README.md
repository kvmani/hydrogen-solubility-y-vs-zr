# presentations/

## Purpose
Store presentation assets derived from documented results.

## Goes In
- Slide decks (`.pptx`, `.pdf`) and exported figures used for talks/reviews
- Figure source notes linking slides to run IDs
- Deck manifests (`*_manifest.json`) used to generate slides

## Does NOT Go In
- Primary raw simulation data
- Untraceable screenshots without run context

## Mission Link
Communicates validated findings while preserving traceability to reproducible runs.

## Required For Major Updates
Every major result set or feature addition must include:
- one `.pptx` deck
- one `.pdf` export of the same deck

## Generator
Use:
- `python tools/presentation/generate_lab_meeting_ppt.py --scan-root results --output-dir presentations --deck-title \"<title>\" --require-pdf`

Style is enforced by script (Arial fonts, black title/footer bars, 20/80 content split).
