# Cron Watchdog Silent State, Window Dedup & Execution Discipline

## Context & Lifecycle

The TikTok Feed Watchdog (`feed_session_watchdog.py`) is executed periodically as a Hermes scheduled cron job to inspect batch runs across farm clusters (`kibe` and `admin`) and dispatch Telegram reports.

### Key Operational State Files
- State file: `D:/Taadaa/runtime/<cluster>/cron-state/feed_session_reported.json` (and `follow_session_reported.json` for follow mode)
- Lock file: `<state_file>.proc_lock`
- Live session folders: `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/row-<row>-<HHMMSS>`

## Idempotency and the Cron `[SILENT]` Contract

When `feed_session_watchdog.py` runs:
1. It reads `reported_sessions` from `cron-state/feed_session_reported.json`.
2. It evaluates whether any session window (`ca1_phien1`, `ca1_phien2`, `ca2_phien1`, `ca2_phien2`, `ca3_phien1`, `ca3_phien2`, `ca4_phien1`, `ca4_phien2`) has finished runs that haven't been claimed yet.
3. If all completed session windows for the target date(s) have already been reported, `messages` remains empty and the script terminates cleanly (exit code 0, 0 bytes on stdout).
4. **Hermes Cron Rule:** When running as a scheduled cron job without new events to deliver, the coordinator must return exactly `[SILENT]` to avoid sending spam/empty notifications to chat channels.

## Terminal Guard Timeout Invariant

On Windows agent runners supervised by runtime guards:
- Foreground terminal commands without an explicit timeout parameter trigger `[GUARD_FOREGROUND_TIMEOUT_MISSING]`.
- Always supply `timeout: 60` (or `timeout <= 60`) for foreground watchdog invocations:
  ```bash
  python "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py"
  ```
- Do not conclude script failure or file missing when stdout is empty; verify `reported_sessions` in `feed_session_reported.json` and compare against the live directory run timestamps.
