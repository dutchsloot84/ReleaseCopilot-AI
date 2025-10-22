#!/usr/bin/env bash
set -euo pipefail

ruff format --check .
ruff check --output-format=github .
mypy --config-file pyproject.toml
make check-generated
git diff --check
