# Triage Coordinator ThreadPoolExecutor Hang, Stale Runner Lease, and Farm Cron Stall

## Symptom
1. Operator notices scheduled shifts (e.g. Ca tối / evening shift) have not run any machines.
2. Telegram bot `Report Lock Device` sends an alert with dozens of machines locked (>30 mins overdue) under a single PID with status `handoff` or `queued_v2`.
3. Hermes `agent.log` logs repeated `Job 'phase9-runner-tiktok-feed' already running — skipping` on every 15-minute tick.
4. `D:/Taadaa/runtime/<host>/cron-state/runner-live-lease/<day>.json` holds a PID that has exceeded its planned run time.

## Root Cause
1. **Default `ThreadPoolExecutor.__exit__` blocking:** In Python's standard library `ThreadPoolExecutor`, exiting a `with ThreadPoolExecutor(...) as executor:` block invokes `executor.shutdown(wait=True)`. Even if the coordinator outer watchdog cancels futures and builds fallback artifacts, the process cannot terminate if one or more worker threads remain blocked in an underlying ADB or network socket call without cooperative cancellation.
2. **Cascading Cron Lockout:**
   - The coordinator Python process and its parent PowerShell launcher remain alive in Windows Task Manager.
   - The runner live lease file (`runner-live-lease/<day>.json`) continues to treat the batch as active because the recorded PID is still alive.
   - Hermes Cron scheduler treats the job as still running and skips every subsequent scheduled tick.
   - Device locks held by the stuck PID remain in `~/.codex/device-locks/` with status `handoff` or `queued_v2` until manually reaped or killed.

## Remediation Sequence
1. **Identify stuck process chain:**
   - Inspect `runner-live-lease/<day>.json` for the current day's lease PID.
   - Verify child processes: `wmic process where ParentProcessId=<pid> get CommandLine,ProcessId`.
2. **Terminate the hung coordinator chain:**
   - Terminate only the specific stuck PowerShell and Python coordinator PIDs.
3. **Clean stale lease & unblock scheduler:**
   - Delete `runner-live-lease/<day>.json`.
   - Clear/release stale `handoff` locks owned by the dead PID under `~/.codex/device-locks/`.
4. **Trigger catch-up / re-arm cron:**
   - Invoke `cronjob(action='run', job_id='<runner_job_id>')` to immediately dispatch the due shift.

## Architectural Prevention
- Subclass `ThreadPoolExecutor` to override `__exit__` with `self.shutdown(wait=False, cancel_futures=True)` (`_FailClosedThreadPoolExecutor`), ensuring the coordinator exits immediately upon watchdog deadline expiration without waiting for orphaned child worker threads.
