# Developer shortcuts. Day-to-day science work uses ./hsol (see docs/workflow.md).
.PHONY: help install check lint test docs docs-linkcheck

SPHINX ?= python -m sphinx

help:
	@echo "make install         install runtime + dev dependencies"
	@echo "make check           lint + tests + docs build (run before every commit)"
	@echo "make lint | test | docs | docs-linkcheck"

install:
	python -m pip install -r requirements-dev.txt -r requirements-docs.txt

lint:
	ruff check src tests hsol
	ruff format --check src tests hsol
	bash -n tools/hpc/check_vasp_installation.sh tools/hpc/discover_vasp_modules.sh

test:
	python -m pytest -q

docs:
	$(SPHINX) -W -q -b html docs docs/_build/html

docs-linkcheck:
	$(SPHINX) -W -q -b linkcheck docs docs/_build/linkcheck

check: lint test docs
