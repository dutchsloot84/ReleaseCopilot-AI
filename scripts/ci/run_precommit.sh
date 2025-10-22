#!/usr/bin/env bash
set -euo pipefail

ruff check --output-format=github .
ruff format --check .
pre-commit run codespell --all-files
pre-commit run check-yaml --all-files
pre-commit run detect-private-key --all-files
make check-generated
git diff --check
