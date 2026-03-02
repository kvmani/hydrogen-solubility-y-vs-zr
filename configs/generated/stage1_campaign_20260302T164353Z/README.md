# Stage-1 Campaign Output

Generated convergence campaign configs for Stage-1 host validation.

## Generated With
`tools/plan_stage1_campaign.py --base-config configs/stage1_y_host_validation_v1.yaml --base-config configs/stage1_zr_host_validation_v1.yaml --sweeps both --include-reference --write-json-plan`

## Artifacts
- Plan CSV: `configs/generated/stage1_campaign_20260302T164353Z/stage1_campaign_plan.csv`
- Config files: one YAML per campaign point
