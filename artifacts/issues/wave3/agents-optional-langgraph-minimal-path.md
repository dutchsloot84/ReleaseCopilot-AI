## Agents (Optional): LangGraph minimal path

Generated automatically from backlog/wave3.yaml on 2025-10-15T23:23:09-07:00 (America/Phoenix · no DST).

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- requirements-agents.txt; src/agents/langgraph/ with AuditAgentGraph.
- Wrap deterministic nodes; add LLM summary/risk narrative node.
- Phoenix-stamped JSON in artifacts/orchestrator/.
- Orchestrator dispatch supports ‘langgraph-runner’; UI shows narrative.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Touch `requirements-agents.txt` only to append the minimal LangGraph extra (no pin drift); confirm the lockstep with existing optional agent deps.
- Add a new `src/agents/langgraph/__init__.py` and `src/agents/langgraph/graph.py` exporting an `AuditAgentGraph` factory that wires deterministic nodes plus an LLM summary/risk narration node.
- Update or create orchestrator wiring under `src/releasecopilot/orchestrator/langgraph_runner.py` (or equivalent orchestrator registry module) so `rc orchestrator --runner langgraph-runner` dispatches to the new graph.
- Extend UI narrative rendering within `ui/pages/orchestrator.py` (or existing orchestrator status component) so the LLM output is surfaced without altering layout contracts.
- Emit Phoenix-aware JSON artifacts by adding an `artifacts/orchestrator/langgraph/` writer in `src/tracking/artifacts.py`, using `ZoneInfo("America/Phoenix")` and existing run metadata (run_id/git_sha/generated_at).
- Sequence: dependency check → graph module scaffold → orchestrator integration → artifact serialization → UI update → documentation/test updates.

### Key code snippets
```python
# src/agents/langgraph/graph.py
from zoneinfo import ZoneInfo
from langgraph.graph import StateGraph


def AuditAgentGraph(*, timezone: ZoneInfo | None = None) -> StateGraph:
    """Return the deterministic LangGraph audit workflow.

    The graph must avoid nondeterministic branching, accept a run payload dict,
    and emit structured summaries without logging secrets. Phoenix (America/Phoenix)
    is the default timezone for timestamped nodes to honor scheduling rules.
    """

    tz = timezone or ZoneInfo("America/Phoenix")
    # add nodes: load -> enrich -> summarize -> risk
    graph = StateGraph()
    graph.add_node("load_context", load_context_node(tz=tz))
    graph.add_node("summarize", llm_summary_node())
    graph.add_node("risk", risk_narrative_node())
    graph.add_edge("load_context", "summarize")
    graph.add_edge("summarize", "risk")
    graph.set_entry_point("load_context")
    graph.set_finish_point("risk")
    return graph
```

```diff
# src/releasecopilot/orchestrator/registry.py
@@
 RUNNERS = {
     "default": DefaultRunner(),
+    "langgraph-runner": LangGraphRunner(factory=AuditAgentGraph),
 }
```

```python
# artifacts/orchestrator/langgraph/run.json schema excerpt
{
    "$id": "artifacts/orchestrator/langgraph/run.json",
    "type": "object",
    "required": ["run_id", "git_sha", "generated_at", "timezone", "summary", "risk"],
    "properties": {
        "generated_at": {"type": "string", "format": "date-time"},
        "timezone": {"const": "America/Phoenix"},
    },
}
```

### Tests (pytest; no live network)
- `tests/agents/langgraph/test_audit_agent_graph.py::test_graph_execution_deterministic` ensures node order and outputs are stable when seeded fixtures are reused.
- `tests/agents/langgraph/test_audit_agent_graph.py::test_risk_node_uses_summary` mocks the LLM layer to verify risk narrative captures summary data without secrets.
- `tests/orchestrator/test_langgraph_runner.py::test_dispatch_and_artifact_written` uses `tmp_path` to assert Phoenix timestamps and JSON schema compliance.
- Edge cases: missing optional dependencies raises clear `ImportError`; artifact writer handles retries/pagination stubs from orchestrator payloads.
- Add coverage measurement via existing `pytest --cov=src/agents/langgraph --cov=src/releasecopilot/orchestrator` target to remain ≥70%.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/orchestrator.md` under the optional agents section:

> The LangGraph audit path is opt-in via `rc orchestrator --runner langgraph-runner`. When enabled, the runner emits Phoenix-aware (`America/Phoenix`) summaries and risk narratives to `artifacts/orchestrator/langgraph/`. Ensure optional agents extras from `requirements-agents.txt` are installed before execution.

Update `README.md` integrations table:

> **LangGraph Audit (optional)** – Provides deterministic audit summaries with Phoenix timezone timestamps. Run `pip install -r requirements-agents.txt` to enable, then trigger via the orchestrator CLI.

### Risk & rollback
- Risks: schema drift between orchestrator payloads and LangGraph nodes; nondeterministic LLM prompts altering tests; artifact path mismatches causing UI regressions.
- Rollback: revert `src/agents/langgraph/`, orchestrator registry updates, UI narrative changes, and artifact writer adjustments; remove added extras from `requirements-agents.txt` if needed.
- No data migrations are introduced; disabling the runner restores prior behavior.


## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Verify deterministic node ordering and stable artifact schema in tests.
- Run ruff/black/mypy and ensure coverage gate ≥70% before submission.
- Confirm artifacts embed `run_id`, `git_sha`, and `generated_at` in America/Phoenix.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Adopt LangGraph-based audit runner with deterministic Phoenix-stamped outputs.
- **Note:** Optional dependency footprint lives in `requirements-agents.txt`; installation is opt-in for agent workflows.
- **Action:** Update orchestrator registry, emit Phoenix JSON artifacts, and surface the new risk narrative in the UI.

**Labels:** wave:wave3, mvp, area:agents, priority:medium
