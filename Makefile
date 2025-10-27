.PHONY: setup lint typecheck test gen-wave

setup:
	poetry install
	pre-commit install

lint:
	poetry run ruff check .
	poetry run ruff format --check .

typecheck:
	poetry run mypy .

test:
        poetry run pytest

gen-wave:
	python main.py generate --spec backlog/wave3.yaml --timezone America/Phoenix --archive
