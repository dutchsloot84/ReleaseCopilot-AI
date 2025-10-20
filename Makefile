PYTHON ?= python3

.PHONY: gen-wave3 check-generated lint lint-fix

gen-wave3:
	$(PYTHON) main.py generate --spec backlog/wave3.yaml --timezone America/Phoenix

check-generated:
	./scripts/ci/check_generator_drift.sh

lint:
	pre-commit run --all-files --show-diff-on-failure

lint-fix:
	ruff check . --fix
	ruff format .
