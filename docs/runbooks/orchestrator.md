# Orchestrator Operations (America/Phoenix)

Phoenix (America/Phoenix) remains the canonical timezone for planning, dispatching, and auditing orchestrator workflows. The timezone does not observe daylight saving time, so all scheduling references should anchor to Mountain Standard Time (UTC-7) year-round. When converting timestamps, prefer explicit offsets and include Phoenix-local copies in manifests and chat summaries.

## Slash-command overview

ChatOps users can manage orchestrator timelines through the following slash-commands. Always validate that the rendered timestamps reflect America/Phoenix unless a manifest explicitly authorizes a different timezone.

### `rc orchestrator plan`

Generate or refresh a mission outline plan:

```bash
rc orchestrator plan \
  --wave 3 \
  --timezone America/Phoenix \
  --output artifacts/orchestrator/plan.json
```

- Produces Phoenix-aware milestones with Decision / Note / Action markers for each checkpoint.
- Stores the artifact under `artifacts/orchestrator/` so reviewers can link it in pull requests.
- Supports `--at "2025-04-18T09:00:00"` when you need to regenerate a plan effective at a specific Phoenix-local timestamp.

### `rc orchestrator dispatch`

Execute previously generated plans without recomputing schedules:

```bash
rc orchestrator dispatch \
  --plan artifacts/orchestrator/plan.json \
  --timezone America/Phoenix
```

- Reuses the Phoenix timestamps embedded in the plan file to avoid DST drift.
- Emits Decision / Note / Action markers for every dispatched task to maintain traceability.
- Accepts `--dry-run` to preview the Phoenix schedule without triggering downstream hooks.

## Phoenix-aware scheduling tips

- Always confirm the orchestrator command output contains the `America/Phoenix` label before sharing or committing artifacts.
- When cross-functional teams require other timezones, duplicate the Phoenix schedule and include both references in documentation instead of replacing the canonical timezone.
- Update the plan artifact immediately after any Decision or Action changes so dispatch inherits the correct Phoenix timestamp windows.

## Related runbooks

- [`docs/runbooks/orchestrator_dispatch.md`](orchestrator_dispatch.md) – legacy dispatcher procedures; defer to this page for slash-command usage.
- [`docs/promptops/human_actions.md`](../promptops/human_actions.md) – human-in-the-loop orchestration expectations tied to Phoenix checkpoints.
