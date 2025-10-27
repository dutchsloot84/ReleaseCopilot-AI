.PHONY: setup lint typecheck test

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
