Act as a release reviewer against the active MOP.

Verify:
- Lint/format, mypy clean; tests pass; coverage ≥ gate.
- Tests mock network/AWS; retries/pagination covered; edge cases included.
- IAM least privilege; **no secrets logged**; Phoenix cron DST documented (if used).
- Artifacts deterministic with run metadata.
- Docs + CHANGELOG updated; PR includes canonical Decision:/Note:/Action: markers.

Return PASS/FAIL with a short, actionable defect list.
