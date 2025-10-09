# Human-in-the-Loop Tracking

Wave 1 maintains manual actions alongside Codex automation to ensure least-privilege security checks and delivery verification.

## Authoring Actions
- When a sub-prompt requires human follow-up, add an entry to `actions/pending_actions.json`.
- Each object records the wave, PR reference, action summary, owner, due date (Phoenix time), target stack, related artifact, and labels.
- Example entry:
  ```json
  {
    "wave": "Wave 1",
    "pr": "#2",
    "action": "Approve SNS topic policy (require SecureTransport)",
    "owner": "John Doe",
    "status": "Pending",
    "due": "2025-10-15",
    "stack": "BudgetAlertsTopic",
    "artifact": "infra/cdk/core_stack.py",
    "labels": ["human-action", "wave:1"]
  }
  ```

## Lifecycle
1. **Create** – Codex or a maintainer seeds the JSON entry when the sub-prompt describes a manual approval.
2. **Surface** – `tools/render_actions_comment.py` renders a sticky PR comment titled `⚠️ Outstanding Human Actions` on every open or synchronize event.
3. **Track** – The GitHub Action applies labels from the entry (e.g., `human-action`, `wave:1`) so the project board relies solely on labels.
4. **Complete** – Humans respond to the PR comment with “done ✅” or tick the checkbox in the comment. The entry status is updated to `Complete` in the JSON during the next automation pass.

## Best Practices
- Use Phoenix dates even when the team is distributed.
- Never store secrets in the JSON or PR comment output.
- Keep the action summary concise so it fits in the rendered Markdown table.
- Remove completed entries promptly to keep the dashboard accurate.
