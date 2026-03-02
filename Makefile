.PHONY: lint test docs-check present init-run-y

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
