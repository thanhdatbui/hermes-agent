# Hermes Stale Watchdog & Subagent Coordination

## Overview
On the Taadaa Phone Farm, Hermes operates in a **Coordinator / Worker** split:
- **Coordinator**: Dispatches worker subagents to investigate/reproduce/fix/test, while coordinator remains silent waiting for worker completion.
- **Worker**: Autonomous subagent executing up to 15-20 tool calls within a 15-minute budget.
- **Watchdog (`hermes_stale_watchdog.py`)**: Monitored via cron to detect real stalls/hangs and alert to Telegram, while remaining completely silent (exit 0) during normal operation.

Synchronized script locations:
- Local runtime: `%LOCALAPPDATA%\hermes\scripts\hermes_stale_watchdog.py`
- Cloud sync: `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\hermes_stale_watchdog.py`

---

## State Files & Architecture

1. `farm_coordinator_phase.json`:
   - Records current coordinator phase per session (`ALERT`, `WORKER_RUNNING`, etc.).
   - Contains `dispatched_at` (or `updated_at`) timestamp `d_at` when coordinator spawned a worker.
2. `watchdog_state.json`:
   - Tracks heartbeat per session (`last_beat`, `current_tool_start`, `current_tool`, `parent_session_id`).
3. `stale_alert_sent.json`:
   - Anti-spam cache to ensure at most one alert is emitted per stall incident per session.

---

## Core Lessons & Pitfalls

### 1. Threshold Alignment with Worker Budget (600s -> 900s)
- **Problem**: Previously `DEFAULT_THRESHOLD_SECONDS = 600.0` (10 minutes). When a worker performed complex tasks within its legitimate 15-minute budget (up to 900s), the watchdog tripped at minute 10, firing false positive stall alerts while the worker was actively functioning.
- **Fix**: Align `DEFAULT_THRESHOLD_SECONDS` to `900.0` (15 minutes).
  ```python
  CANARY_THRESHOLD_SECONDS = 1500.0   # 25 minutes for real device canary
  DEFAULT_THRESHOLD_SECONDS = 900.0   # 15 minutes for normal code fix / inspect / tools
  WORKER_TIMEOUT_SECONDS = 1200.0     # 20 minutes for worker execution
  ```

### 2. Multi-turn Subagent Candidate Collision (`parent_session_id`)
- **Problem**: When a coordinator runs multiple turns across a session, multiple subagents are dispatched sequentially, all sharing the same `parent_session_id == sid`.
- If the watchdog only filters `cstate.get("parent_session_id") == sid`, it can pick up an old, finished subagent from a previous turn whose heartbeat stopped hours ago, resulting in a false stall alert.
- **Fix**: Filter candidates using the dispatch timestamp `d_at` with a 30s grace window:
  ```python
  child_candidates = [
      (csid, cstate) for csid, cstate in watchdog_sessions.items()
      if isinstance(cstate, dict)
      and cstate.get("parent_session_id") == sid
      and float(cstate.get("current_tool_start") or cstate.get("last_beat") or 0) >= (d_at - 30.0)
  ]
  ```

### 3. Dual-path Synchronization Requirement
Any change to `hermes_stale_watchdog.py` must be applied to both:
- `C:\Users\Kibe\AppData\Local\hermes\scripts\hermes_stale_watchdog.py`
- `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\hermes_stale_watchdog.py`
Both files must pass `python -m py_compile` and a direct invocation check (`exit code 0`).

---

### 4. Mock Test Session Artifacts Polluting Shared State Files (`test_*` / `mock_*` Phantom Hangs)
- **Problem / Symptom**: Watchdog fires an absurd alert to Telegram, e.g.:
  `⚠️ [CẢNH BÁO HERMES TREO - 2026-10-02 08:04:29] Session test_guard_session_v2 đang im lặng 34513 phút (vượt ngưỡng 15m)! - Tool: delegate_task`
- **Root Cause**: Unit test suites (e.g. `test_scope_lock_guard_v2.py` or guard plugin tests) writing mock session entries (`test_*`, `mock_*`, `parent_*`, `coord_session_*`) directly into production/shared state files (`farm_coordinator_phase.json`, `watchdog_state.json`) without teardown/isolated `tmp_path`.
  When an old mock record in `watchdog_state.json` (from weeks earlier, e.g. Sept 8) collides with a fresh test run that sets `phase: "WORKER_RUNNING"` or `"ALERT"` in `farm_coordinator_phase.json`, the watchdog calculates elapsed time against the ancient timestamp (`now - 1788832311 = 34,513 minutes`), generating false alarms claiming Hermes is hung.
- **Triage & Remediation**:
  1. **Triage**: Check `farm_coordinator_phase.json` and `watchdog_state.json`. Any session ID starting with `test_`, `mock_`, `parent_`, or with an elapsed time in the thousands of minutes is test artifact pollution, NOT an actual hung process or Hermes stall.
  2. **Cleanup**: Remove mock session keys from both `farm_coordinator_phase.json` and `watchdog_state.json`, then clear `stale_alert_sent.json` cache and invoke `python hermes_stale_watchdog.py` to verify exit code 0 and silent stdout.
  3. **Prevention & Defense-in-Depth**:
     - *In test suites*: Never mutate production `%LOCALAPPDATA%\hermes` state files directly; use `tmp_path`, `monkeypatch.setattr`, or enforce `try ... finally` fixtures that pop mock session keys.
     - *In `hermes_stale_watchdog.py`*: Explicitly filter out test prefixes (`if sid.startswith(('test_', 'mock_', 'parent_', 'coord_session_')):`), ensuring mock runs never trigger live cron notifications.

