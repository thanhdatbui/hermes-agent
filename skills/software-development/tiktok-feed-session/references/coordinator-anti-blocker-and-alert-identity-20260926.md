# Coordinator anti-blocker and alert identity (2026-09-26)

## Why this reference exists
A feed incident exposed repeated coordinator errors: treating a consumer-repo boundary as an absolute ban after explicit user authorization, stopping after inspection instead of continuing to patch/test/canary, refusing valid stale-fixture updates, and attempting canary row selection from serial alone when one machine had eight accounts.

## Required execution ladder
When the user explicitly asks to fix/recover until done, continue:

`inspect -> exact artifact/anchor -> worker patch -> focused test -> target-scoped canary -> closeout`

Do not end the task after inspection. Dirty files outside the allowlist, stale tests, missing live evidence, or a first worker timeout are not terminal blockers.

- Explicit user authorization permits a shared/canonical cross-repo fix within a written allowlist. Keep worker ownership, focused tests, diff evidence, and all destructive/live safety gates.
- A stale mock/fixture may be corrected when the failure proves the fixture no longer matches the current flow. Do not alter production merely to force a test pass.
- A worker timeout is transient: retry with a narrower prompt (maximum two retries); do not silently downgrade to BLOCKED.
- Use `DONE` only when code/tests pass and required canary passes. Use `PARTIAL` when offline code/tests pass but a required canary is pending. Use `BLOCKED` only after the ladder is exhausted and include command, exit code, and concrete log/error evidence.

## Alert identity gate
For `[MÁY N]` canaries, resolve in this order:

1. The incident alert or run artifact for the same run.
2. `device_id`/serial.
3. The username/account in that same record.
4. Workbook row.

Never choose one of several accounts on a machine from serial alone. `inspect_machine.py N` proves current physical state only; Launcher/Home now is not proof of the account or UI state at incident time. If the current artifact lacks the incident account, report `TARGET_ACCOUNT_UNRESOLVED` and locate the exact run artifact/alert source; do not run a canary against a guessed account.

## Evidence separation
Keep these fields separate in reports:

- `incident-time identity`: account/row from the alert's run artifact.
- `current live state`: fresh inspect/screenshot/XML now.
- `offline code evidence`: diff and focused test output.
- `live canary evidence`: official runner exit code, final status, screenshot/XML paths.

Never let an unproven live root cause erase a proven offline code/test result, and never claim a live fix from offline tests alone.

## Safety preserved
This procedure does not relax bans on `pm clear`, arbitrary logout, manual ADB tap/input as a substitute for a code fix, destructive cleanup, or fabricated evidence. It changes only coordinator progress discipline and identity resolution.