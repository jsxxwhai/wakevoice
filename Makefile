PYTHON ?= python3
PIP ?= pip

.PHONY: install test lint run-once run-wake clean

install:
	$(PIP) install -e .

bootstrap:
	$(PYTHON) scripts/bootstrap.py

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/ tests/ || true

run-once:
	$(PYTHON) -m assistant.cli --once

run-wake:
	$(PYTHON) -m assistant.cli --wake

clean:
	rm -rf build dist *.egg-info .pytest_cache __pycache__
