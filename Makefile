PYTHON ?= python3

.PHONY: gen-wave3 check-generated lint lint-fix

gen-wave3:
	PYTHONPATH=$${PYTHONPATH:+$${PYTHONPATH}:}src:. $(PYTHON) -m releasecopilot.cli_releasecopilot generate --spec backlog/wave3.yaml --timezone America/Phoenix

check-generated:
	$(PYTHON) -m tools.hooks.check_generator_drift

lint:
	pre-commit run --all-files --show-diff-on-failure

lint-fix:
	ruff check . --fix
	ruff format .
