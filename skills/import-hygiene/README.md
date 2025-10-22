# Import Hygiene Skill Card

Decision:
- Adopt automated import organization via ruff/isort so contributors share a single canonical ordering.

Note (2025-02-14 America/Phoenix):
- Auto-fix commits pushed by CI are tagged `[skip ci]` to avoid workflow loops and always use the message `style: organize imports (ruff isort)`.

Action:
- Apply this checklist to every new module and whenever adjusting imports in existing files.

## Purpose
Ensure imports are grouped consistently (future → stdlib → third-party → first-party → local) to eliminate recurring ruff I001 violations.

## Steps
1. Run `ruff check --fix .` to sort imports within each section using the shared configuration in `pyproject.toml`.
2. Run `ruff format .` so formatting is stable before hooks execute.
3. Execute `pre-commit run --all-files` to mirror the CI pipeline and confirm no further adjustments are necessary.
4. Push your branch; if CI adds an auto-fix commit, fetch and integrate it before merging.

## Validations
- `ruff check .` reports no `I001` (import order) warnings.
- `ruff format --check .` returns clean formatting.
- CI reports a clean working tree after linting; otherwise follow the troubleshooting guide in `CONTRIBUTING.md`.

## Rollback
If the workflow needs to be disabled temporarily, revert the CI job additions in `.github/workflows/ci.yml` while leaving the `pyproject.toml` configuration intact so developers can continue linting locally.
