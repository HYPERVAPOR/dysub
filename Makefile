VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install test lint format clean

install:
	$(PIP) install -e packages/dysub-core[dev]
	$(PIP) install -e packages/dysub-input-local
	$(PIP) install -e packages/dysub-input-douyin
	$(PIP) install -e apps/webui

test:
	$(PYTHON) -m pytest --cov=dysub_core --cov-report=term-missing

lint:
	$(VENV)/bin/ruff check packages apps tests
	$(VENV)/bin/ruff format --check packages apps tests

format:
	$(VENV)/bin/ruff format packages apps tests
	$(VENV)/bin/ruff check --fix packages apps tests

clean:
	rm -rf dist *.egg-info .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name *.egg-info -exec rm -rf {} + 2>/dev/null || true
