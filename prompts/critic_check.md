Act as a release reviewer against the active MOP.

Verify:
- Lint/format, mypy clean; tests pass; coverage ≥ gate.
- Tests mock network/AWS; retries/pagination covered; edge cases included.
- IAM least privilege; **no secrets logged**; Phoenix cron DST documented (if used).
- Artifacts deterministic with run metadata.
- Docs + CHANGELOG updated; PR includes canonical Decision:/Note:/Action: markers.
- Lint/format clean: `ruff check --select E402,F404,I .` returns 0 findings.
- `from __future__ import annotations` (if present) follows the module docstring before all imports/code.
- Imports grouped stdlib → third-party → first-party (`releasecopilot`); no local shadowing.
- `pre-commit` installed; `pre-commit run --all-files` clean; docs reflect current commands.

Return PASS/FAIL with a short, actionable defect list.
