# Timeout and cross-evidence reconciliation

## Observed pattern

A candidate changed both a watchdog classifier and a workbook-sync wrapper. The first closeout run executed only the sync test file and scored 69/100 because the classifier branches and output-file edge cases were not directly covered. After adding focused tests, a local combined run reported `58 passed`, but a later exact closeout invocation timed out at the gate's 120-second pytest cap.

## Reliable reconciliation sequence

1. Treat the gate timeout as a failed closeout result, not as stale infrastructure.
2. Run the two mapped test files independently from the repository root with the gate interpreter and pytest mode.
3. Run the exact combined command: `pytest tests/test_feed_session_watchdog.py tests/test_hermes_taikhoan_sync_cron.py --tb=short -q`.
4. If the combined command appears stuck, run the watchdog module with `-v -s` and isolate the first slow node. In the observed case, the suspected window-reconcile test passed alone in under one second and the module passed in about three seconds; the combined command then passed in about three seconds.
5. Only after the exact combined command has a fresh exit code 0 rerun `closeout_gate.py`. Keep the gate result distinct from local pytest evidence.

## Evidence boundaries

- A worker's “done” report does not prove the second file was edited; inspect `git diff --stat` and run the test yourself.
- A prior gate score is bound to its recorded commit and does not authorize a later HEAD.
- A generic or old canary receipt is not evidence for a new watchdog/sync candidate. If the release guard requires live canary, use the official targeted runner or report the blocker.
- Do not hand-edit receipts or audit logs to bypass TTL, SHA, or scope binding.
