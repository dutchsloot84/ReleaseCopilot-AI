## QA Focus & Regression Heuristics (YAML-driven)

Generated automatically from backlog/wave3.yaml on 2025-10-15T23:23:09-07:00 (America/Phoenix · no DST).

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- risk.yaml with critical_paths + label_weights.
- Score per story/module with reasons; top N endpoint.
- UI list with reason tooltips; JSON export section.
- Artifacts: Release Notes + Validation Doc + Exports.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Create `config/risk.yaml` defining `critical_paths` and `label_weights` per acceptance criteria.
- Implement scoring engine `src/releasecopilot/qa/risk_scorer.py` that ingests YAML config, computes per-story/module scores with justification text.
- Add API endpoint `src/releasecopilot/qa/api.py` exposing `/qa/top` to return top N stories with reasons, defaulting to Phoenix timezone metadata on responses.
- Update UI (`ui/pages/qa_focus.py`) to render a list with tooltip details and reference JSON export links in `artifacts/qa/`.
- Ensure orchestrator pipeline writes Release Notes/Validation/Exports artifacts as dependencies; link new QA artifacts to them.
- Sequence: config file → scoring engine → API endpoint → UI updates → artifact wiring → docs/tests.

### Key code snippets
```yaml
# config/risk.yaml
critical_paths:
  - path: src/releasecopilot/
    weight: 3
label_weights:
  regression: 2
  performance: 1
```

```python
# src/releasecopilot/qa/risk_scorer.py
def score_items(items: list[dict[str, Any]], config: RiskConfig, *, tz: ZoneInfo | None = None) -> list[RiskScore]:
    """Return sorted risk scores with reasons; deterministic ordering."""

    zone = tz or ZoneInfo("America/Phoenix")
    scored = []
    for item in items:
        reasons = []
        score = 0
        for label in item.get("labels", []):
            if label in config.label_weights:
                score += config.label_weights[label]
                reasons.append(f"label:{label}")
        if item.get("module") in config.critical_paths:
            score += config.critical_paths[item["module"]]
            reasons.append("critical-path")
        scored.append(RiskScore(key=item["key"], score=score, reasons=reasons, generated_at=datetime.now(tz=zone)))
    return sorted(scored, key=lambda r: (-r.score, r.key))
```

```json
// artifacts/qa/risk_scores.schema.json (excerpt)
{
  "type": "object",
  "required": ["run_id", "git_sha", "generated_at", "timezone", "scores"],
  "properties": {
    "timezone": {"const": "America/Phoenix"},
    "scores": {"type": "array", "items": {"type": "object", "required": ["key", "score", "reasons"]}}
  }
}
```

### Tests (pytest; no live network)
- `tests/qa/test_risk_scorer.py::test_score_items_orders_by_weight` ensures deterministic ordering and reason list.
- `tests/qa/test_risk_scorer.py::test_score_items_handles_missing_labels` covers edge cases.
- `tests/qa/test_api.py::test_top_endpoint_limits_results` verifies Phoenix metadata in response.
- UI component test `tests/ui/test_qa_focus_page.py::test_tooltips_render_reasons` using Streamlit testing harness.
- Confirm coverage ≥70% on new QA modules and maintain fixture determinism via `tests/fixtures/qa/risk_config.yaml`.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/qa.md`:

> Risk scoring uses `config/risk.yaml` to weight critical paths and labels. The `/qa/top?limit=N` endpoint returns Phoenix-stamped (`America/Phoenix`) scores with justification text for audit trails. UI pages surface the same data with hover tooltips explaining each reason.

Update `README.md` analytics section:

> QA Focus metrics feed Release Notes, Validation Docs, and Export bundles. JSON exports are available under `artifacts/qa/` with run metadata (`run_id`, `git_sha`, `generated_at`).

### Risk & rollback
- Risks: YAML misconfiguration causing zero scores, tooltip rendering errors, inconsistent artifacts with release documents.
- Rollback: revert `config/risk.yaml`, QA scorer modules, API/ UI updates, and remove artifacts if necessary.
- No data migrations; artifacts regenerate from orchestrator runs.


## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Validate YAML parsing errors surface clearly; include schema validation tests.
- Run ruff/black/mypy on QA modules and ensure pytest coverage threshold met.
- Confirm artifacts list includes Release Notes + Validation Doc + Exports cross-reference.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Introduce YAML-driven QA risk scoring with Phoenix-aware exports.
- **Note:** Config weights require coordination with QA leads before changes.
- **Action:** Add `risk.yaml`, implement scoring engine/API/UI updates, and document artifact linkage.

**Labels:** wave:wave3, mvp, area:analysis, priority:high