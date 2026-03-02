.PHONY: lint test docs-check present init-run-y extract-metrics

RUN_DIR ?= results/runs/20260302_Y_stage1_dft_001

lint:
	@echo "TODO: add lint pipeline (e.g., ruff + markdownlint)."

test:
	@python tools/validate_config.py \
		configs/stage1_y_host_validation_v1.yaml \
		configs/stage1_zr_host_validation_v1.yaml

docs-check:
	@python tools/validate_config.py \
		configs/stage1_y_host_validation_v1.yaml \
		configs/stage1_zr_host_validation_v1.yaml

present:
	@python tools/presentation/generate_lab_meeting_ppt.py \
		--scan-root results \
		--output-dir presentations \
		--deck-title "Y vs Zr Hydrogen Solubility - Major Update" \
		--basename major-update \
		--max-results 10

init-run-y:
	@python tools/init_run.py configs/stage1_y_host_validation_v1.yaml

extract-metrics:
	@python tools/extract_metrics.py --run-dir $(RUN_DIR)
