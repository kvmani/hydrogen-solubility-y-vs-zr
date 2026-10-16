# configs/

| Path | What it is | Edit? |
|---|---|---|
| `campaigns/*.yaml` | one file per stage: what to compute for Y, Zr and H₂ | yes - the scientific source of truth |
| `campaigns/common_settings.yaml` | physics shared by every calculation (smearing, PAW datasets, ...) | rarely, and then re-run everything |
| `campaigns/converged_settings.yaml` | ENCUT and k-point spacing from `hsol analyze convergence` | once, after Stage 1a |
| `site.example.yaml` → `site.yaml` | your cluster settings (not in git) | once per cluster |
| `generated/` | run configs written by `hsol plan` (not in git) | never |

Campaign keys are documented in [`docs/config_schema.md`](../docs/config_schema.md); the order of
campaigns in [`docs/workflow.md`](../docs/workflow.md).
