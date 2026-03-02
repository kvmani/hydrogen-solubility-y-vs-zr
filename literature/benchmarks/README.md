# Benchmark Extraction (Stage 0)

## Purpose
Provide machine-readable quantitative anchors for hydrogen solubility modeling, with explicit provenance and extraction status.

## Files
- `tss_benchmark_records.csv`: normalized benchmark records (numeric values and formula records).
- `provenance_map.md`: row-by-row source traceability notes.

## Record Schema
Each row in `tss_benchmark_records.csv` uses:
- `record_id`: stable identifier.
- `system`: `Y` or `Zr`.
- `phase_context`: phase/condition context from source.
- `temperature_min_K`, `temperature_max_K`: temperature window for the record.
- `pressure_value`, `pressure_unit`: pressure context if applicable.
- `quantity_name`, `quantity_value`, `quantity_unit`: measured/derived quantity.
- `relationship`: equation text when the record is formula-based.
- `source_key`, `doi`: reference pointer.
- `source_location`: equation/table/figure location descriptor.
- `extraction_method`: `direct_text`, `table_value`, `equation_transcription`, or `manual_entry_planned`.
- `data_status`: one of:
  - `extracted`: quantitative value directly captured from source text/table.
  - `proxy_non_tss`: useful quantitative anchor but not a strict alpha-phase TSS point.
  - `manual_entry_planned`: source identified, final reference points will be entered manually by project owner.

## Scope Note
This first extraction pass prioritizes values/equations recoverable from accessible primary-source text. Full alpha-phase TSS-vs-T reference curves for Y and Zr will be added manually by project owner in a later step.
