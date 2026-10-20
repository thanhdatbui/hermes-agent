# Telegram Session Auto-Resume Preservation across Host Reboot

## Background & Failure Mode
When daily host reboots run at fixed schedules (05:20, 11:20, 17:20), `farm_preflight_daily_reset.py` marks active Telegram sessions as `.resume_pending` (`restart_interrupted`) so the Hermes Gateway automatically resumes the coordinator session post-boot.

### The Two Stalls (Incident 20/10/2026)
1. **Narrow Lookback Window (20m):** `preserve_in_flight_sessions` used `lookback_minutes=20`. A session whose last message was exchanged 30 minutes before reboot (e.g. 10:49:50 before 11:20:01) was silently discarded before examining messages.
2. **Assistant-Last Trap (`last_role == 'assistant'`):** When the assistant just completed tool operations and reported status/asked the user for steering, `last_role` was `assistant` with no pending `tool_calls`. The script concluded the turn was "finished" and skipped preservation, causing a silent stall where the bot never resumed and the user was left hanging for over an hour.

## Implementation Pattern
In `services/Taadaa_Service/farm_preflight_daily_reset.py`:
1. Use `lookback_minutes=60` in `_run_preflight()`.
2. Inspect recent tool history within the lookback window:
   ```python
   has_recent_tools = bool(_fetch_one(
       conn, lock,
       "SELECT 1 FROM messages WHERE session_id = ? AND role = 'tool' AND timestamp >= ? AND active = 1 LIMIT 1",
       (sid, cutoff.timestamp()),
   ))
   in_flight = last_role in ("user", "tool") or (
       last_role == "assistant" and (_has_tool_calls(tool_calls) or has_recent_tools)
   )
   ```
3. Sync verified code immediately to the active Windows service path `C:/Taadaa_Service/farm_preflight_daily_reset.py`.

## Verification Discipline
- Run `pytest D:/Taadaa/tools/tests/test_farm_preflight_daily_reset.py -q`.
- Foreground execution may exceed 60s under disk/DB load; use `background=True, notify_on_complete=True` if needed.
- **NEVER** hallucinate or report test counts (e.g. "131/131 passed") before the command has exited 0 with actual inspectable stdout.
- Verify both the source repository and the deployed service copy before marking DONE.
