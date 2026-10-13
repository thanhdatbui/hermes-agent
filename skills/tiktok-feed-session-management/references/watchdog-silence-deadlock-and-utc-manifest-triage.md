# Watchdog Silence, Session Deadlock & UTC Manifest Timezone Triage

## Overview & The "Missing Report" Symptom

Hermes watchdogs (`feed_session_watchdog.py`, `follow_session_watchdog.py`) run periodically (every 5 minutes) with `no_agent: true`. Under the watchdog pattern:
- **Empty stdout means SILENT**: Hermes suppresses notifications when there is nothing new to report.
- When users ask *"Why is it 09:24 and there is no report for nurture or follow runs that started this morning?"*, it usually indicates that the watchdog is silently waiting due to a gating condition, or is blocked in a session deadlock.

---

## 3 Root Causes of Watchdog Silence

### 1. Active Window In-Flight (Normal Operation)
- If the current time is within a session window (e.g., Session 2/2 from 08:00 to 12:00, checking at 09:24), the runner is still actively processing batches of phones.
- Watchdogs are designed to report **only after all expected machines have finished** OR **after the window has closed and the runner is idle**.
- As long as machines are still running and the window has not elapsed, silence is intentional and expected.

### 2. Back-to-Back Session Overlap & Global Runner Busy Deadlock
- If Session 1 (06:00 - 08:00) finishes slightly late (e.g. at 08:02:39), but the scheduler spawns Session 2 at 08:00:36, the system-wide check `is_feed_runner_active()` remains `True` without returning to `False`.
- To avoid permanently blocking Session 1's report, `feed_session_watchdog.py` implements session-level uncoupling via `is_cluster_session_busy(date_live, session_runs, win_end_hm, global_runner_busy)`:
  - It checks whether the session's latest run has completed (`_is_session_manifest_completed`).
  - It checks whether a subsequent run for the day has already started (`_has_later_session_run_started`).
  - If both conditions hold, the previous session is released (`decision = False`) even if the global runner is busy.

### 3. UTC vs Local Timezone Skew in Manifest Parsing (Critical Bug Pattern)
- `python_runner` logs timestamps in `run_manifest.json` using UTC ISO 8601 strings (e.g. `"end_time": "2026-10-13T01:02:39.217492+00:00"` or ending with `Z`).
- If the watchdog extracts `end_hm` via naive string slicing (`end_time.replace("T", " ").split(" ", 1)[-1][:5]`), it extracts UTC hours (`01:02`).
- Comparing `"01:02" >= "08:00"` (HCMC local time) evaluates to `False`.
- Consequently:
  - `_is_session_manifest_completed` returns `False`.
  - `is_cluster_session_busy` falls back to `global_runner_busy = True`.
  - `can_report_session` blocks delivery for Session 1 because it believes the session never reached completion within the window.
  - The watchdog stays completely silent for hours.

---

## Diagnostic Checklist for Coordinator

When troubleshooting silent watchdogs:

1. **Inspect Reported State First (O(1)):**
   - Check `D:/Taadaa/runtime/<cluster>/cron-state/feed_session_reported.json` and `follow_session_reported.json`.
   - Confirm if the session key (e.g. `2026-10-13_ca1_phien1`) is present.

2. **Check Live Directory Manifests:**
   - Locate the session folder: `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/row-<row>-<HHMMSS>/<subrun>/run_manifest.json`.
   - Read `end_time`. Check whether it is UTC (`+00:00` or `Z`) and verify its equivalent in local time (`Asia/Ho_Chi_Minh`).

3. **Check Active Process State:**
   - Run a focused psutil check for runner patterns (`multi_machine_feed_session`, `run-feed-session.ps1`, `run_follow`).
   - Identify whether current busy state belongs to the current session or a subsequent session.

4. **Verify Session Busy Decision:**
   - Evaluate `_is_session_manifest_completed()` with timezone conversion:
     ```python
     dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
     if dt.tzinfo is not None:
         dt = dt.astimezone(HCMC)
     end_hm = dt.strftime("%H:%M")
     ```
   - Ensure `end_hm >= win_end_hm` compares local time against local window end.

---

## Delegation Contract Guidelines for Watchdog Scripts

When dispatching Worker subagents to patch `feed_session_watchdog.py` (>1,500 lines monolith):
- Enforce Gate 2: Anchor must be verified O(1) (`count == 1`).
- Contract format requirements:
  - `TASK_KIND: EDIT`
  - `TARGET_FILE: D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`
  - `OLD_STRING: <<< ... >>>`
  - `NEW_STRING: <<< ... >>>`
  - `FOCUSED_TEST: python -m py_compile scripts/feed_session_watchdog.py`
    *(Note: Avoid full absolute path with spaces like `tiktok-luot nuoi acc` in `FOCUSED_TEST` as guard regex tokenization breaks on whitespace; use repo-relative path instead).*
