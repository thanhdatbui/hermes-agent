# Row 1 stop protocol and worker-cap verification (2026-08-27)

## What was learned
The row-1 operation used a local wrapper rather than the repository's parallel batch entrypoint:

- `f2a_row1_batch.py`: custom row-1 orchestrator; one `subprocess.run(...)` at a time, so effective concurrency is **1**.
- `python_runner/run_batch_live_2fa.py`: repository batch entrypoint; `MAX_BATCH_SIZE = 10`, `--max-workers` defaults to 10, and execution uses `ThreadPoolExecutor(max_workers=min(cfg.max_workers, len(reserved_targets)))`.

Always inspect the actual command line and source before reporting “max worker”.

## Safe stop procedure
1. Poll the tracked batch process and record its PID.
2. Stop the batch parent.
3. Enumerate descendants whose command is the batch wrapper or `run_capture_phase_b.py`; stop only descendants of that batch PID. Do not stop Gateway or unrelated cron workers.
4. Verify with a real process table (`psutil`/`tasklist` with command-line inspection). A search command can match its own shell text and produce a false positive.
5. Inspect every remaining device-lock alias. For an active-looking lock, independently verify the recorded owner PID is absent before recovery.
6. If the owner is dead and the lock belongs to the same project, use the device-lock library's guarded `SAME_PROJECT_RECOVERY` takeover and release path. Do not delete lock JSON files manually.
7. Keep `handoff` locks from failed/blocked runs for audit unless the operator explicitly requests release and the recovery proof is complete.
8. Verify Gateway is still running and cron jobs remain enabled; stopping the batch must not pause cron.

## Evidence rules
- A stopped worker is not a success. Any target interrupted during UI work remains unverified until workbook, journal, and lock-release checks pass.
- `DEVICE_LOCK_UNAVAILABLE`, `BLOCKED_ENABLED_2FA_WITHOUT_RECOVERABLE_JOURNAL`, account-switch ambiguity, password-gate, and UI-target ambiguity are evidence-bearing terminal outcomes for the current batch pass; do not blind-retry them.
- When the wrapper's log repeats the same target/result three or more times, treat it as a loop defect and stop the batch before the next cron window.
- Report counts as: target count, verified success, terminal failures/blockers, and interrupted/in-progress targets. Never collapse these into a single “done” number.

## Privacy
Do not include passwords, OTPs, 2FA secrets, mail tokens, or full serials in reports or skill references. Use machine/row and masked identifiers only when needed.
