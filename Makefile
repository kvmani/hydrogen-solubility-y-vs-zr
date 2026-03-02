.PHONY: lint test docs-check present init-run-y extract-metrics hpc-dryrun-y hpc-smoke-y hpc-submit-y hpc-batch-dryrun

RUN_DIR ?= results/runs/20260302_Y_stage1_dft_001
Y_CONFIG ?= configs/stage1_y_host_validation_v1.yaml
ZR_CONFIG ?= configs/stage1_zr_host_validation_v1.yaml
COMPILER_MODULE ?= <compiler_module>
MPI_MODULE ?= <mpi_module>
VASP_MODULE ?= <vasp_module>

lint:
	@echo "TODO: add lint pipeline (e.g., ruff + markdownlint)."

test:
	@python tools/validate_config.py \
		$(Y_CONFIG) \
		$(ZR_CONFIG)

docs-check:
	@python tools/validate_config.py \
		$(Y_CONFIG) \
		$(ZR_CONFIG)

present:
	@python tools/presentation/generate_lab_meeting_ppt.py \
		--scan-root results \
		--output-dir presentations \
		--deck-title "Y vs Zr Hydrogen Solubility - Major Update" \
		--basename major-update \
		--max-results 10

init-run-y:
	@python tools/init_run.py $(Y_CONFIG)

extract-metrics:
	@python tools/extract_metrics.py --run-dir $(RUN_DIR)

hpc-dryrun-y:
	@tools/hpc/run_vasp_pipeline.sh --mode dryrun --config $(Y_CONFIG)

hpc-smoke-y:
	@tools/hpc/run_vasp_pipeline.sh --mode smoke --config $(Y_CONFIG) \
		--compiler-module $(COMPILER_MODULE) \
		--mpi-module $(MPI_MODULE) \
		--vasp-module $(VASP_MODULE)

hpc-submit-y:
	@tools/hpc/run_vasp_pipeline.sh --mode submit --config $(Y_CONFIG) \
		--compiler-module $(COMPILER_MODULE) \
		--mpi-module $(MPI_MODULE) \
		--vasp-module $(VASP_MODULE) \
		--require-potcar true

hpc-batch-dryrun:
	@tools/hpc/run_vasp_batch.sh --mode dryrun $(Y_CONFIG) $(ZR_CONFIG)
