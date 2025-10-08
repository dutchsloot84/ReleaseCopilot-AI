# Bugfixes

## Wave 1

- Restored the CLI export surface at the package root and aligned the IAM secrets
  retrieval policy Sid with the infrastructure tests to keep the Wave 1 release
  pipeline green.
- Ensured dotenv loading prefers the repository `.env` before package fallbacks
  and deduplicated secret access policies so the synthesized template exposes
  exactly four least-privilege statements.
- Reinstated the ``AllowSecretRetrieval`` Sid with explicit Jira, Bitbucket, and
  webhook secret ARNs while keeping the inline IAM policy to the four permitted
  Wave 1 statements.
