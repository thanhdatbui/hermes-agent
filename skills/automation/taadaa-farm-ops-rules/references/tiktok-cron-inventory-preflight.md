# TikTok cron inventory preflight and chained-reporting reference

Use this reference when a Gmail → TikTok cron reports `Code N | Hoàn tất`, especially when Phase 2 exits within seconds.

## Proven investigation sequence

1. Anchor the exact cron job ID, timestamp, and phase output.
2. Run the TikTok detector only (`_detect_clean.py`) in read-only mode. Do not run `_run_all_targets.py`, acquire device locks, or start workers during diagnosis.
3. Require all three artifacts before calling Phase 2 a worker run:
   - fresh target-selection manifest
   - fresh batch directory
   - per-target worker logs/results
   If Phase 2 exits in seconds and only the first artifact (or no artifact) exists, classify it as preflight/target-detection/launcher failure, not UI, OTP, or account failure.
4. Inspect the inventory workbook semantically, not only by row count. In the observed `Accounts` layout, date markers were pasted into the `Device ID` column in otherwise valid machine blocks. Valid date values such as `DD/MM/YYYY`, `DD-MM-YYYY`, or `YYYY-MM-DD` are metadata markers and must not create a false duplicate-machine conflict. Unknown non-date values and two different real serials for one machine remain fail-closed.
5. Preserve the detector's numeric exit code. A child failure such as detector exit `2` must not be wrapped as `SystemExit("...")`, which converts it to an outer exit `1`. Emit the diagnostic on stderr and exit with the child code.
6. Scheduled launchers must not inject `--full-scope-takeover` / `-fullScopeTakeover` by default. Reclaiming locks is an explicit operator action, not a cron default.
7. Summary parsers must never use `Hoàn tất` as the fallback for an unknown or non-zero phase. Prefer the exact preflight error, then a real summary line; return a non-zero aggregate when any phase or verified target fails.

## Regression fixture shape

Create a temporary `Accounts` workbook with:

- one machine mapped to the same real serial on multiple rows
- one date marker in that machine's `Device ID` cell
- a second machine with a valid serial

Expected: the global and target-scoped inventory loaders resolve the real serials and ignore only the date marker. A fixture with two different real serials for one machine must still raise `TARGET_INVENTORY_CONFLICT`.

## Verification gate

After a code change, run the focused inventory/status tests, `py_compile` for detector/runner/pipeline, `git diff --check`, and the real detector against the current workbook. Do not claim the registration flow is fixed unless a separately authorized live run produces worker-level proof.

## Reporting format

Keep the user-facing report concise and fact-only:

- Gmail: distinguish proxy/device-lock preflight failures from registration/UI failures.
- TikTok: state whether detection, lock reservation, worker startup, or UI/OTP failed.
- Include counts and artifact paths when useful; redact credentials, OTPs, tokens, and serials unless explicitly required.
