# Feed Session Watchdog Operation & Troubleshooting Reference

## Architecture & Reporting Semantics

`feed_session_watchdog.py` monitors multi-machine feed sessions per shift (Ca) across clusters (`kibe`, `admin`):
- 4 Shifts / 8 Session Windows per day (Phiên 1 and Phiên 2 per shift).
- Each shift targets an active row based on parity (e.g. Day 15 -> Row 1/Row 3/Row 5/Row 7; Day 16 -> Row 2/Row 4/Row 6/Row 8).
- Atomic claim & report persistence in:
  - `D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json` (Feed & general status)
  - `D:/Taadaa/runtime/kibe/cron-state/follow_session_reported.json` (Follow-specific mode)

## Cron Execution & Silent Output Rule

When `feed_session_watchdog.py` runs via scheduled cron:
1. **Silent Suppression (`[SILENT]`):**
   - If there are no newly completed shifts ready to report, the watchdog produces no output on stdout (or logs only to telemetry files).
   - In scheduled cron mode, when stdout is empty or nothing new is reportable, the agent MUST return exactly `[SILENT]`.
2. **Reporting Gates (`can_report_session`):**
   - If the current session window is active (`now_hm < window_end_hm`) and runner is active, reporting is deferred until completion.
   - If already reported (session key present in `feed_session_reported.json`), the session is skipped.
3. **Guard Compliance:**
   - Always run foreground terminal commands with explicit `timeout <= 60` to adhere to `[GUARD_FOREGROUND_TIMEOUT_MISSING]`.
   - Never search internal cron output dirs (`~/.hermes/cron/output/...`) or broad root scans that trigger system protection guards.
