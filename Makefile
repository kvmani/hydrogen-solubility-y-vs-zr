.PHONY: lint test docs-check present init-run-y extract-metrics report-run hpc-preflight hpc-preflight-inputs hpc-preflight-all hpc-patch-scheduler hpc-dryrun-y hpc-smoke-y hpc-submit-y hpc-batch-dryrun plan-stage1

RUN_DIR ?= results/runs/20260302_Y_stage1_dft_001
Y_CONFIG ?= configs/stage1_y_host_validation_v1.yaml
ZR_CONFIG ?= configs/stage1_zr_host_validation_v1.yaml
HPC_CONFIG_PATHS ?= $(Y_CONFIG) $(ZR_CONFIG)
HPC_PARTITION ?= <partition>
HPC_ACCOUNT ?= <account>
HPC_REQUIRE_POTCAR ?= true
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

report-run:
	@python tools/generate_run_report.py --run-dir $(RUN_DIR)

hpc-preflight:
	@python tools/hpc/preflight_scheduler_configs.py --fail-if-unready $(HPC_CONFIG_PATHS)

hpc-preflight-inputs:
	@python tools/hpc/preflight_input_decks.py --fail-if-unready --require-potcar $(HPC_REQUIRE_POTCAR) $(HPC_CONFIG_PATHS)

hpc-preflight-all: hpc-preflight hpc-preflight-inputs

hpc-patch-scheduler:
	@python tools/hpc/preflight_scheduler_configs.py \
		--set-partition "$(HPC_PARTITION)" \
		--set-account "$(HPC_ACCOUNT)" \
		--write \
		--fail-if-unready \
		$(HPC_CONFIG_PATHS)

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

plan-stage1:
	@python tools/plan_stage1_campaign.py \
		--base-config $(Y_CONFIG) \
		--base-config $(ZR_CONFIG) \
		--sweeps both \
		--include-reference \
		--write-json-plan
