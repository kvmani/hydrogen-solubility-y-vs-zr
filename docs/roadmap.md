# Roadmap

Each stage ends at a gate: the listed evidence must exist (as `converged` runs plus a note in
`progress/`) before the next stage counts as started. Tooling status: ✅ ready, ⬜ open.

| Stage | Goal | Tooling | Gate to pass |
|---|---|---|---|
| 0 Literature | Experimental anchors and hypotheses H1–H4 (`literature/lit_review.md`) | ✅ benchmarks CSV | Y and Zr anchors DOI-traceable; TSS curve points entered (⬜ manual entry pending) |
| 1a Convergence | ENCUT and k-spacing for both metals | ✅ `stage1_convergence.yaml`, `analyze convergence` | ≤ 1 meV/atom vs most accurate point; values in `converged_settings.yaml` |
| 1b Host lattice | PBE a, c of α-Y and α-Zr | ✅ `stage1_relax.yaml` | relaxed cells converged; deviation from experiment recorded |
| 2 H energetics | ΔE_T, ΔE_O; site preference | ✅ `stage2_h_energetics.yaml` | both sites computed per metal; final sites checked; supercell-size check (4×4×3, `tag`) ⬜ |
| 3 Vibrations | ZPE and F_vib(T) of H; site stability | ✅ `stage3_vibrations.yaml` | no unexplained imaginary modes; ΔZPE per site |
| 4 Hydrides | Hydride per-H free energy | ✅ `stage4_hydrides.yaml`, `stage4_hydride_vibrations.yaml` | fluorite MH₂ relaxed and vibrated; Zr δ-hydride model choice justified ⬜ |
| 5 Solubility model | x_H(T,p), TSS(T), plateau p(T); Y vs Zr | ✅ `analyze solubility` | trend Y ≫ Zr reproduced or the discrepancy explained; comparison with benchmarks ⬜ |
| 6 Manuscript | Figures, tables, methods | ⬜ (`docs/manuscript_blueprint.md`) | every claim traced to run ids and citations |

Stages 2 and 4a only need Stage 1, so they can run in parallel; Stage 3 needs Stage 2 and
Stage 4b needs 4a.

## Open items, in priority order

1. Run Stage 1a on the cluster and fill in `configs/campaigns/converged_settings.yaml`.
2. Enter experimental TSS(T) points for Y and Zr (`literature/benchmarks/`), then add a benchmark
   overlay to `hsol analyze solubility`.
3. Supercell-size check: repeat Stage 2 at 4×4×3 with a `tag` and compare ΔE_s.
4. Decide the Zr hydride model (fluorite ZrH₂ vs ε-ZrH₂ vs δ-ZrH₁.₅ ordered cells).
5. Beyond the ideal lattice gas for Y at high H/Y (H–H pair interaction) if Stage 5 shows it matters.

## Standing rules

- Slurm work always goes `dryrun → smoke → submit`; `hsol` enforces it.
- No result is used unless its run is `converged` and its manifest is complete.
- Changed physics means a new run id (`tag`), never an overwrite.
- Docs, campaigns and code change together; `make check` passes before merging.
- Major results get a lab-meeting deck (`tools/presentation/`); decks are not committed.
