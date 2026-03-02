.PHONY: lint test docs-check

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
