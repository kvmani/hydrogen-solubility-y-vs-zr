# Provenance Map For `tss_benchmark_records.csv`

## y1993_theta_upper_1073, y1993_theta_upper_1373
- Source: `maeda1993_diffusivity_solubility_y` (DOI: 10.1039/FT9938904375)
- Extraction basis: Methods text in article PDF (`ft9938904375`) stating pressure cap and corresponding concentration bounds.
- Trace note: pressure < 2.6 Pa corresponds to H/Y < 0.23 (1073 K) and < 0.022 (1373 K).

## y1993_diffusion_activation
- Source: `maeda1993_diffusivity_solubility_y` (DOI: 10.1039/FT9938904375)
- Extraction basis: Abstract statement reporting diffusion activation energy.
- Trace note: activation energy reported as 510 meV.

## y1994_solubility_law, y1994_interaction_parameter
- Source: `maeda1994_concentration_effects_y` (DOI: 10.1039/FT9949001979)
- Extraction basis: Abstract/model equations and interpretation section from article text.
- Trace note:
  - Solubility form: `p = k [theta/(1-theta)]^2`.
  - Present-study interpretation indicates near-zero long-range interaction parameter (`w ≈ 0`) over tested theta range.

## zr1945_saturation_20c
- Source: `hall1945_solubility_zr` (DOI: 10.1039/TF9454100306)
- Extraction basis: Table/discussion text in PDF (`tf9454100306`).
- Trace note: mean saturation value around 236 cm3(STP)/g at 20 C for hydrogen pressures around 550-650 mmHg.

## zr1954_alpha_phase_comp_limit, zr1954_saturation_648K, zr1954_saturation_836K, zr1954_two_phase_pressure_eq
- Source: `rees1954_interpretation_zr` (DOI: 10.1039/TF9545000343)
- Extraction basis: phase summary text and explicit reported equations/values.
- Trace note:
  - Alpha-phase composition range reported as up to ~5 atom% H.
  - Reported saturation examples: 232 cm3/g at 375 C and 222 cm3/g at 563 C.
  - Two-phase pressure relation reported: `log10(p0/mmHg) = 5.875 - (5150/T_K)`.

## y_tss_curve_points_pending, zr_tss_curve_points_pending
- Status: `needs_digitization`
- Reason: direct TSS/TSSP point clouds from primary figures/tables require a dedicated digitization pass to avoid transcription error.
- Planned next step: generate structured point files (`*_tss_points.csv`) with uncertainty columns and per-point source coordinates.
