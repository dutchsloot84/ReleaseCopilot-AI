#!/usr/bin/env bash
set -euo pipefail

if [[ "${TZ:-}" != "America/Phoenix" ]]; then
  echo "[simulate_orchestrator_event] Please export TZ=America/Phoenix before running." >&2
  exit 2
fi

EVENT_PATH=${1:-"$(dirname "$0")/sample_issue_comment_event.json"}
if [[ ! -f "$EVENT_PATH" ]]; then
  echo "[simulate_orchestrator_event] Event payload not found: $EVENT_PATH" >&2
  exit 1
fi

export GITHUB_EVENT_PATH="$EVENT_PATH"
export GITHUB_EVENT_NAME="issue_comment"
export ALLOWED_ROLES="MEMBER,TRIAGE"
export ALLOWED_USERS=""

python "$(dirname "$0")/check_comment_permissions.py"

PHOENIX_RUN_ID="$(TZ="America/Phoenix" date +"%Y-%m-%dT%H-%M-%S%z")"
export PHOENIX_RUN_ID

mkdir -p artifacts/orchestrator

if command -v rc >/dev/null 2>&1; then
  echo "[simulate_orchestrator_event] Invoking rc orchestrator dispatch (Phoenix run $PHOENIX_RUN_ID)" >&2
  rc orchestrator dispatch --event-path "$GITHUB_EVENT_PATH"
else
  echo "[simulate_orchestrator_event] rc CLI not found; skipping dispatch invocation." >&2
fi

python - <<'PY'
import json
import os
from pathlib import Path

event_path = Path(os.environ["GITHUB_EVENT_PATH"])
phoenix_run_id = os.environ.get("PHOENIX_RUN_ID")

payload = json.loads(event_path.read_text(encoding="utf-8"))
command_line = next(
    (line.strip() for line in payload.get("comment", {}).get("body", "").splitlines() if line.strip().startswith("/orchestrate")),
    "",
)
record = {
    "command": command_line,
    "issue": payload.get("issue", {}).get("number"),
    "phoenix_run_id": phoenix_run_id,
    "workflow_run_id": "local-simulation",
}
log_path = Path("artifacts/orchestrator/dispatch-log.ndjson")
with log_path.open("a", encoding="utf-8") as handle:
    json.dump(record, handle, sort_keys=True)
    handle.write("\n")
print(f"Wrote {log_path} with Phoenix run {phoenix_run_id}")
PY
