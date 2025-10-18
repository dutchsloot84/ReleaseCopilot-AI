# Offline Testing with Cached Payloads

**Reference:** `artifacts/issues/wave3/tests-mocked-jira-bitbucket-e2e-with-cached-payloads.md`

Wave 3 testing hardens the offline `rc audit` command so auditors can work without
network access. Cached payloads for Jira and Bitbucket live under
`tests/fixtures/cached/` and include Phoenix-stamped summary metadata. To
validate the full flow, run:

```bash
pytest tests/e2e/test_audit_cached_payloads.py --cov
```

The test seeds the cache directory, runs the CLI, and asserts the resulting JSON
and Excel artifacts conform to the schemas guarded in `tests/contracts/`. Set
`RC_CACHED_PAYLOAD_DIR` to reuse the fixtures manually when invoking the CLI.
All timestamps are asserted in `America/Phoenix` to satisfy the Wave 3
schedule guarantees.
