# Taadaa tools workbook-recovery closeout pattern

## What was verified

The account-provisioning change passed the scoped reviewer with `APPROVED`, score `88/100`, exit code `0`, and focused tests passing. The reviewed scope was:

- `ensure_row_accounts.py`
- `tests/test_ensure_row_accounts.py`

## Durable implementation pattern

When `Path.replace()` of an `.xlsx` fails because OneDrive temporarily holds the destination:

1. Save the modified workbook to a sibling `.tmp.xlsx`.
2. Validate the temporary workbook with `openpyxl.load_workbook(..., read_only=True)`.
3. Retry the atomic replace with bounded backoff (three attempts in the verified implementation).
4. Only after retries fail, copy the original destination to a rollback backup, copy the validated temporary workbook, reopen the destination to verify it is a readable workbook, delete the temporary/rollback files only after verification, and restore the backup if fallback fails.
5. Emit failure telemetry instead of silently swallowing host-config or Telegram errors. Telegram send helpers must return `False` for HTTP failure/exception, not `True` merely because the request was attempted.

## Review/evidence discipline

- Add offline tests for host-config load failure telemetry, recognized/unknown config stems, retry-then-success, permanent replace denial with verified fallback, and Telegram 4xx/5xx return status.
- Normalize CRLF/LF before review; phantom whole-file diffs can trigger payload truncation and lower the score.
- Keep farm execution evidence separate from mocked tests. Unit tests prove failure-path behavior; they do not prove OneDrive or Telegram production availability.
- Scope the gate to the exact source/test files and verify the candidate-bound audit record. Preserve unrelated dirty files.

## Remaining reviewer caveat

The fallback copy is verified and rollback-protected but is not fully atomic under concurrent external writers. Treat that as a residual risk, not as proof of production concurrency safety; if that risk is later addressed, add a separate focused concurrency test and review it as a new scoped change.
