# OAuth Watchdog Checkpoint Triage

Use this runbook when a pool healer reports `Timeout bắt OAuth code`.

## Classification before retry

Inspect the saved browser screenshot and, when needed, OCR it. Treat the generic timeout as a fallback label only:

- `PHONE_CHECKPOINT`: Google asks for a phone number. Stop recovery for that account; do not repeatedly retry or bypass the checkpoint.
- `TOO_MANY_ATTEMPTS`: the recovery-code option is unavailable/rate-limited. Treat as cooldown, not as a missing callback.
- `CAPTCHA_CHALLENGE`: classify and retain screenshot evidence separately from timeout.
- `Confirm your recovery email`: select that route and fill the configured recovery email. If the account value is blank, use the approved fallback only for this field; never overwrite a non-empty account value.
- `TIMEOUT`: use only when no more specific checkpoint was observed.

## Targeted rerun gate

Before rerunning one account, fetch the paginated GPM inventory and require exactly one matching profile. Confirm the provider connection and its current `isActive`/`testStatus`; do not run the broad pool healer when a single account is requested. Run the existing account-specific recovery path and require fresh log/screenshot or a successful OAuth callback as evidence. A process exit code alone is not proof of recovery.

## Telemetry hygiene

Normalize and deduplicate failure records by lowercase/trimmed email before telemetry and alert rendering, preserving the first observed error. This prevents duplicate records for one account from inflating the pool alert.

## Evidence from the 2026-10-05 incident

The account `luunhu290719@gmail.com` showed `Confirm your recovery email` available while `Get a verification code` was unavailable because of too many attempts. Other accounts showed phone checkpoints. This demonstrated that the old generic timeout label concealed materially different recovery actions.
