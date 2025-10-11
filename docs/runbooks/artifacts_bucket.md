# Artifacts Bucket Runbook

## Prefix and retention overview

| Prefix | Purpose | Lifecycle |
| --- | --- | --- |
| `releasecopilot/artifacts/json/` | Primary JSON reports published by the CLI or Lambda exporter. | Transition to Standard-IA after 45 days, Glacier Deep Archive after 365 days, retain 5 non-current versions. |
| `releasecopilot/artifacts/excel/` | Excel workbook exports for release reviews. | Transition to Standard-IA after 45 days, Glacier Deep Archive after 365 days, retain 5 non-current versions. |
| `releasecopilot/temp_data/` | Intermediate cache for resumable audits. | Expire objects after 10 days to control storage costs. |
| `releasecopilot/logs/` | Diagnostic bundles emitted alongside artifacts. | Transition to Standard-IA after 30 days, expire after 120 days. |

TLS-only access (`aws:SecureTransport=true`), bucket-owner enforced object
ownership, and default SSE-S3 encryption are required invariants. Bucket
policies also deny uploads that omit `x-amz-server-side-encryption=AES256`.

## Adjusting retention safely

1. Capture the current lifecycle configuration with `aws s3api get-bucket-lifecycle-configuration` and store it alongside run metadata (date/time, Phoenix timezone, change reason, requester, commit SHA).
2. Update the CDK constants in `infra/cdk/core_stack.py` if retention needs to
   change. Avoid editing the console policy directly; CDK drift detection will
   overwrite manual changes.
3. Run `pytest -q` and `npx --yes cdk synth` to confirm lifecycle rules and
tests align with the new policy.
4. Deploy via the `cdk-deploy` workflow or `npx --yes cdk deploy` and record the
   deployment timestamp in Phoenix time (America/Phoenix) to maintain the audit
   trail required by the Master Orchestrator Prompt.
5. Validate the lifecycle preview in the S3 console for the affected prefixes
   before the first transition window elapses.

## Recovery and restore checklist

1. Identify the impacted prefix and determine whether the desired version is the
   current object or a prior version (versioning is enabled by default).
2. For current objects, download directly via `aws s3 cp`. For older versions,
   list non-current object versions with `aws s3api list-object-versions` scoped
   to the prefix, then restore the desired version with
   `aws s3api restore-object` (Glacier) or copy it back into place if already in
   S3 Standard/IA.
3. When restoring from Glacier Deep Archive, initiate the restore with an
   expedited retrieval if time-critical; otherwise plan for 12–48 hours before
   data becomes available. Document Phoenix-local restore start and completion
   times for compliance.
4. Once restored, verify downstream consumers (Streamlit UI, Historian) can read
   the object. Remove temporary copies created during recovery to avoid bypassing
   lifecycle policies.

## Phoenix-time considerations

Lifecycle transitions occur on UTC-boundary schedules, but run metadata and any
manual cleanup tasks must log timestamps in America/Phoenix. When scheduling
additional cleanup (for example, a Lambda to purge abandoned uploads), express
cron expressions in UTC while documenting the Phoenix-local equivalent to avoid
DST ambiguity.

## Cost optimisation notes

- Standard-IA transitions for artifacts and logs start after 30–45 days; monitor
  S3 Storage Lens or Cost Explorer for changes in access patterns before lowering
  the thresholds.
- Glacier Deep Archive retention drastically lowers long-term storage costs for
  audit history. Adjust the transition window in `core_stack.py` if audits need
  faster retrieval, but record the trade-off in CHANGELOG and Historian notes.
- Use the managed read/write IAM policies exposed as stack outputs when
  delegating access. Avoid granting wildcard S3 permissions that would undermine
  lifecycle and encryption enforcement.
