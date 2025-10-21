# Correlation & Gaps Engine

**Decision:** Update link precedence and expose Phoenix-stamped gaps endpoints.
**Note:** Artifacts now include input args; document expected payload for consumers.
**Action:** Ship matcher updates, persist metadata, and document new endpoints.

Wave 3 introduces a Phoenix-aware correlation workflow that resolves story links by
inspecting commit messages before branch names and PR titles. The resulting gap
responses expose metadata stamped in the `America/Phoenix` timezone and are
persisted alongside each run artifact.

## CLI Usage

Use the ReleaseCopilot CLI to execute the matcher workflow and emit correlation
artifacts:

```shell
rc matcher correlate \
  --issues data/jira_issues.json \
  --commits data/bitbucket_commits.json \
  --window-hours 24
```

Each invocation writes a run document under `artifacts/issues/wave3/correlation/`
containing:

- `run_id`, `git_sha`, and `generated_at` metadata in America/Phoenix.
- `args` echoing the CLI inputs (including `window_hours`, issue, and commit paths).
- `summary`, `matched` story/commit tuples, and Phoenix-aware gap payloads for
  `stories_without_commits` and `commits_without_story`.

The CLI also maintains `latest.json` and `latest_summary.json` cache files within the
artifact directory for quick inspection by downstream tooling.

## Gap Endpoints

Both gap endpoints share the following structure:

- `run_id`, `git_sha`, `generated_at`, `timezone`, and `args` metadata.
- `payload` with the list of unresolved stories or orphan commits.

They can be materialised directly from the artifact payload or from the in-memory
helpers located at `src/releasecopilot/gaps/api.py`.

## Timezone Considerations

All timestamps are normalised using `ZoneInfo("America/Phoenix")`, ensuring that
scheduling and auditing remain DST-free as mandated by the Wave 3 mission outline.
