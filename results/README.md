# results/

| Path | Written by | Content |
|---|---|---|
| `runs/<run_id>/` | `hsol prepare`, `run`, `collect` | inputs, raw VASP outputs, `manifest.json`, `metrics.json`, `report.html` |
| `INDEX.md`, `index.csv` | `hsol status` / `collect` | every run with status, energy and a link to its report |
| `analysis/convergence/` | `hsol analyze convergence` | Stage-1a tables, plots, recommended settings |
| `analysis/solubility/` | `hsol analyze solubility` | site energetics, TSS(T), plateau pressure, summary |
| `batch_logs/` | `hsol run` | per-invocation summaries (not in git) |

Never edit or delete files in a run directory by hand; formats and the commit policy are in
[`docs/data_model.md`](../docs/data_model.md).
