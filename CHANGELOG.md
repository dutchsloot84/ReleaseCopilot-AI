## [Unreleased]
### Added
- Least-privilege Secrets Manager wiring with secret smoke test CLI and redaction helpers.
- MOP + prompt-chaining scaffolding (`prompts/` templates, runbooks, PR template, Issue form).
- Active MOP index in docs; README quickstart.

### Chore
- Remove placeholderless f-strings flagged by ruff F541.

### Fixed
- Expose CLI functions at the package root to satisfy tests and document the
  supported public interface.
- Align the IAM secrets retrieval policy Sid with infrastructure assertions to
  maintain least-privilege access checks.
