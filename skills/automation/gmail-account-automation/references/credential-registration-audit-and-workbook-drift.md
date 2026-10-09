# Credential, Registration, and Workbook-Drift Audit

Use when an OAuth feeder reports `MISSING_PASSWORD`, an account is absent from Excel, or the operator says the password must exist in registration logs.

## Evidence contract

For every target email, produce a row with:

`email | registration time | machine/device | password source (redacted in chat unless explicitly needed) | GPM profile evidence | workbook state | exact omission cause`

A blank workbook cell is not proof that no password exists. Distinguish:

- `NOT_IN_WORKBOOK`: no matching row in the checked workbook(s).
- `BLANK_PASSWORD_IN_WORKBOOK`: row exists but password cell is empty.
- `PASSWORD_FOUND_IN_REG_LOG`: exact email/username match in the registration artifact, with source path and nearby timestamp/step.
- `PROFILE_ONLY`: GPM profile/cookies exist, but no credential artifact has been verified.
- `RECOVERY_EXCLUDED`: feeder skipped because recovery policy matched; this is separate from missing password.
- `OAUTH_SCRIPT_SKIP`: feeder had a candidate but skipped it at a later gate.

## Procedure

1. Start with exact email and username variants; search only the known registration log directories and the specific GPM/OAuth state files. Do not scan the whole drive.
2. Read surrounding log lines around the exact match. Registration logs commonly identify the machine, profile, `[10] Password` step, result state, and sync/update action in adjacent lines.
3. Cross-check the GPM `profile_data.db` row for profile name/path and creation or update metadata. Treat cookies as session evidence, not as proof of the original password.
4. Cross-check each relevant workbook separately, including all relevant sheets. Record whether the row is absent, present-but-blank, or present-with-value; do not assume one workbook mirrors another.
5. Inspect the registration runner's Excel-write path and result artifact for the target batch. Look for parallel writers, late worker failure, rollback/backup restore, or a batch that logged into GPM without completing the workbook sync.
6. Only after the source is verified may a worker propose a workbook repair. Preserve the original artifact, use a bounded row-level change, and re-read the saved row plus a hash/mtime or equivalent evidence.

## Reporting discipline

- Do not claim a registration date, recovery address, machine, or password from session history alone; session search is a lead, not current-source proof.
- Do not state that an account is “clean” or “not khoalee” until the recovery field is verified from the authoritative row.
- Passwords are secrets: avoid printing them in Telegram unless the operator explicitly requests the value; prefer `FOUND (source=..., fingerprint=...)` in intermediate reports.
- If the audit is incomplete or a worker is still running, report `PENDING_EVIDENCE` rather than filling gaps with plausible values.
