# Gateway Auto-Resume After Reboot: Routing updated_at vs Message Timestamp Pitfall

## Problem & Root Cause

Hermes Gateway features a session preservation and auto-resume mechanism across system reboots:
- Before a scheduled or manual reboot, `farm_preflight_daily_reset.py` calls `preserve_in_flight_sessions(lookback_minutes=60)` to set `resume_pending = true` and `suspended = true` on in-flight sessions in `gateway_routing`.
- On startup after reboot, `_schedule_resume_pending_sessions()` in `gateway/run.py` inspects `gateway_routing` and automatically schedules resumption events for sessions marked with `resume_pending`.
- As a secondary fallback, `session.py` provides `suspend_recently_active(max_age_seconds=3600)` to rescue active sessions after uncontrolled reboots or crashes.

### The Stale updated_at Trap
In Hermes Gateway architecture:
- `entry['updated_at']` in the `gateway_routing` table is updated **ONLY when an incoming user message is received** by the adapter (e.g. at turn kickoff).
- When an agent runs a long turn involving multiple tool calls, subagent delegations, or long builds (e.g. 20-30+ minutes), `entry['updated_at']` in `gateway_routing` remains frozen at the timestamp of the initial user message.
- Consequently, if `preserve_in_flight_sessions` or `suspend_recently_active` checks `entry['updated_at'] >= cutoff` with a 20-minute lookback:
  - An agent actively running tool calls at minute 25 will be judged as "inactive" (`04:55:35 < 05:00:07`) and **dropped without `resume_pending`**.
  - On startup, the gateway sees no pending sessions and sits idle in polling mode, forcing the user to manually ping.

## Remediation & Proper Query Pattern

1. **Query Real Message/Tool Activity:**
   Do not rely solely on `entry.get('updated_at')`. Always inspect the session's actual message activity:
   ```python
   sid = entry.get("session_id")
   with db._lock:
       row_ts = db._conn.execute(
           "SELECT MAX(timestamp) FROM messages WHERE session_id = ? AND active = 1",
           (sid,)
       ).fetchone()
   last_activity_ts = row_ts[0] if (row_ts and row_ts[0]) else None

   # Check both routing entry time and real message/tool time:
   is_recent = (updated >= cutoff) or (
       last_activity_ts is not None and float(last_activity_ts) >= cutoff.timestamp()
   )
   if not is_recent:
       continue
   ```

2. **Extend Lookback Windows:**
   - Preflight reset `lookback_minutes`: Default to **60 minutes** (up from 20).
   - Startup crash recovery `max_age_seconds`: Default to **3600 seconds** (up from 1800).

3. **In-Flight Intent vs Completed Sessions:**
   Maintain the fail-safe:
   - If the last turn was `assistant` and has NO pending tool calls (pure text response delivered), the turn is finished and the session is waiting for user input $\rightarrow$ **Do NOT set `resume_pending`** (avoids unwanted wakeups or repetitive replies).
   - If the last turn was `user`, `tool`, or `assistant` with unreturned tool calls $\rightarrow$ **Mark `resume_pending = true`**.
