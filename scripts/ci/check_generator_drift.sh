#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO_ROOT"

python main.py generate --spec backlog/wave3.yaml --timezone America/Phoenix --archive

git diff --stat --exit-code docs/mop docs/sub-prompts artifacts || {
  echo "Generator drift detected. Run 'python main.py generate --timezone America/Phoenix --spec backlog/wave3.yaml'" >&2
  exit 1
}
