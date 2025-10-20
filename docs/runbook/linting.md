# Linting & Import Hygiene

## Local (before committing)
```bash
pre-commit install
pre-commit run --all-files
# or, directly:
ruff check --fix .
ruff format .
ruff check --select E402,F404,I .
```

## CI behavior

- Optional command-gated autofix (maintainer/label/slash-command).
- Always runs a strict Ruff check; PR fails on any remaining E402/F404/I violations.

## Rules enforced

- F404: `from __future__` must appear right after the module docstring.
- E402: imports must be at the top (after docstring and `from __future__`).
- I*: imports grouped and sorted: stdlib → third-party → first-party (`releasecopilot`).
