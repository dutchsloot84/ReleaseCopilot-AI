# Wave 3 – Sub-Prompt · [AUTO] Agents (Optional): LangGraph minimal path

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

## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.