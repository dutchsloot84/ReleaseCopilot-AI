## PR Template + Orchestration Docs (slash-commands, Phoenix TZ)

Generated automatically from backlog/wave3.yaml on 2025-10-15T23:23:09-07:00 (America/Phoenix · no DST).

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- Template enforces Decision/Note/Action markers.
- Notes quality bar, ≥70% coverage, ruff/black/mypy gates.
- Docs page explains orchestrator plan/dispatch and Phoenix TZ.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Update `.github/pull_request_template.md` to require **Decision/Note/Action** sections with checkboxes for coverage (≥70%), `ruff`, `black`, and `mypy` confirmations.
- Add slash-command documentation to `docs/runbooks/orchestrator.md` describing `rc orchestrator plan` and `rc orchestrator dispatch` flows with Phoenix timezone context.
- Ensure README references the quality bar and timezone requirements in the contributing section.
- Sequence: adjust PR template → expand docs with orchestrator commands and Phoenix scheduling notes → crosslink README.

### Key code snippets
```markdown
<!-- .github/pull_request_template.md excerpt -->
**Decision:** <!-- summarize go/no-go -->
**Note:** <!-- context or caveats -->
**Action:** <!-- follow-up tasks -->

- [ ] Tests updated and ≥70% coverage on touched code (`pytest --cov`).
- [ ] Formatting & linting: `ruff`, `black`, `mypy`.
```

```markdown
# docs/runbooks/orchestrator.md excerpt
## Slash Commands

Use `rc orchestrator plan --timezone America/Phoenix` to generate schedules without DST adjustments. Dispatch runs via `rc orchestrator dispatch --plan artifacts/orchestrator/plan.json` to execute Phoenix-aware workflows.
```

### Tests (pytest; no live network)
- No code changes, but validate documentation references existing CLI tests such as `tests/cli/test_orchestrator.py::test_plan_command_uses_timezone` for accuracy.
- Ensure markdown lint (if configured) passes and docstrings reference Phoenix timezone consistently.

### Docs excerpt (README/runbook)
Add to `README.md` contributing section:

> Pull requests must include **Decision/Note/Action** summaries and confirm lint/format/type gates (ruff, black, mypy) plus ≥70% coverage on touched code. Orchestrator commands assume America/Phoenix for scheduling; override via `--timezone` only when necessary.

Update `docs/runbooks/orchestrator.md` introduction:

> Phoenix (America/Phoenix) remains the canonical timezone for planning and dispatching workflows. Slash-commands from ChatOps should default to this timezone to ensure predictable execution windows.

### Risk & rollback
- Risks: PR template enforcing unchecked boxes might block merges unexpectedly; documentation drift if CLI flags change.
- Rollback: revert `.github/pull_request_template.md` and doc updates; no runtime impact.
- No data migrations or dependency changes.

## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Verify PR template renders correctly on GitHub and does not leak internal links.
- Confirm docs mention lint/format/type gates and Phoenix timezone.
- Run markdown lint if available.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Enforce Decision/Note/Action template and document Phoenix-aware orchestrator commands.
- **Note:** Contributors must acknowledge coverage and lint gates explicitly in PRs.
- **Action:** Update PR template, README, and orchestrator runbook.

**Labels:** wave:wave3, mvp, area:docs, priority:medium
