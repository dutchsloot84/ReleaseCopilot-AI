#!/usr/bin/env bash
set -euo pipefail

export PRE_COMMIT_HOME="${PRE_COMMIT_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/pre-commit}"

python -m pre_commit run --all-files --show-diff-on-failure
git diff --check
