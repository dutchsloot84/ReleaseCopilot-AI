#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "${ROOT_DIR}"

echo "[watchdog] Running ruff autofix..."
ruff check --fix .

echo "[watchdog] Formatting with black..."
black .

echo "[watchdog] Running targeted pytest suite..."
if [ "$#" -gt 0 ];
then
    pytest "$@"
else
    pytest
fi

echo "[watchdog] Autofix routine complete."
