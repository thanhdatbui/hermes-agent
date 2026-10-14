# Farm Reboot Auto-Resume & In-Flight Session Preservation Architecture

## 1. Problem Background & Stale Routing Timestamp Trap
- **The Symptom**: When the host machine undergoes scheduled reboot (`farm_preflight_daily_reset.py`) or sudden restart, interactive Telegram sessions mid-turn (e.g. running deep tool calls or subagents) were silently abandoned and frozen after reboot, requiring the user to manually send another message to wake them up.
- **Root Cause (Stale `entry['updated_at']`)**:
  - In Hermes Gateway architecture, `entry["updated_at"]` in `gateway_routing` is **ONLY updated when an inbound message is received from the user**.
  - During a 20-30+ minute turn where the agent runs dozens of tools/subagents, `entry["updated_at"]` remains frozen at the initial user message timestamp.
  - Preflight reboot routines using `cutoff = now - timedelta(minutes=20)` and checking `if updated < cutoff: continue` falsely classified these active sessions as long-idle and skipped them.

---

## 2. Real Timestamp Extraction & 60-Minute Safe Lookback
To ensure active sessions are never dropped before host reboot:
1. **Query Real Message/Tool Timestamp**:
   Instead of relying on `entry["updated_at"]`, query the latest active message timestamp directly from SQLite:
   ```python
   sid = entry.get("session_id")
   with db._lock:
       row_ts = db._conn.execute(
           "SELECT MAX(timestamp) FROM messages WHERE session_id = ? AND active = 1", (sid,)
       ).fetchone()
   last_activity_ts = row_ts[0] if (row_ts and row_ts[0]) else None
   ```
2. **Dual-Condition Cutoff Evaluation**:
   Consider the session active if EITHER `entry.updated_at >= cutoff` OR `last_activity_ts >= cutoff.timestamp()`:
   ```python
   if updated < cutoff and not (last_activity_ts is not None and float(last_activity_ts) >= cutoff.timestamp()):
       continue
   ```
3. **Nới lỏng lookback window**:
   Use `lookback_minutes = 60` (or `max_age_seconds = 3600`) to cover long tool-use chains.

---

## 3. Discerning In-Flight Turns vs Finished Replies
- **Preserve (`resume_pending = True`)**:
  - `last_role in ('user', 'tool')`
  - `last_role == 'assistant'` AND has non-empty `tool_calls` without a corresponding tool result.
- **Skip (Wait for User)**:
  - `last_role == 'assistant'` with no pending tool calls (the agent already answered and is passively waiting for user input). Auto-resuming finished turns creates spam/hallucinated self-replies.

---

## 4. Post-Boot Gateway Startup Safety (`suspend_recently_active`)
In `gateway/session.py`, `suspend_recently_active` acts as the post-crash / post-boot safety net.
- Uses `_last_message_at(session_id)` to check real message timestamps alongside `entry.updated_at`.
- Sets `resume_pending = True` and `resume_reason = 'restart_interrupted'`.
- On gateway boot, `_schedule_resume_pending_sessions()` synthesizes an internal empty-text event to prompt the agent to inspect state and resume its interrupted work.

---

## 5. Anti-Deception & Coordinator Accountability Invariant
- **Rule**: Coordinator must NEVER output promises like "Em đang cho rà soát..." or "Đang tiến hành..." without an active background process (`terminal(background=True)` or `delegate_task`).
- Reporting an action as in-progress without an active PID or transcript handle is a severe discipline failure.
- When resuming or recovering from reboot, coordinators must report actual empirical state immediately without manufacturing excuses.
