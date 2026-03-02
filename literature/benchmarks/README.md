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
- `extraction_method`: `direct_text`, `table_value`, `equation_transcription`, or `manual_digitization_required`.
- `data_status`: one of:
  - `extracted`: quantitative value directly captured from source text/table.
  - `proxy_non_tss`: useful quantitative anchor but not a strict alpha-phase TSS point.
  - `needs_digitization`: source identified, numeric point extraction pending figure digitization.

## Scope Note
This first extraction pass prioritizes values/equations recoverable from accessible primary-source text. Direct alpha-phase TSS-vs-T point clouds for Y and Zr still require dedicated figure/table digitization from selected sources.
