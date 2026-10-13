# Manifest UTC Timezone & Overlapping Session Deadlock

## Overview

In `feed_session_watchdog.py`, session reporting is governed by `can_report_session` and `is_cluster_session_busy`. When sessions run normally and finish before the window end (e.g. 08:00 for Session 1), a lull occurs between sessions where `is_feed_runner_active()` returns `False`. The watchdog immediately claims and reports the session.

However, when a session exceeds its window end and overlaps with the subsequent session (which spawns automatically on schedule, e.g. at 08:00:36), `is_feed_runner_active()` remains `True` continuously. The watchdog must rely on `is_cluster_session_busy()` to recognize that the prior session has completed and that active runner processes belong to the next session.

---

## Root Cause Analysis: The UTC Timezone Deadlock Trap

### 1. The Symptom
Session 1 (06:00 - 08:00) finishes on devices at 08:02:39, while Session 2 (08:00 - 12:00) spawns at 08:00:36. No reports for Session 1 are delivered to Telegram even by 09:30, despite 100% completion on all devices.

### 2. The Flaw in `_is_session_manifest_completed`
`run_manifest.json` is written by Python runners using UTC ISO 8601 timestamps:
```json
"end_time": "2026-10-13T01:02:39.217492+00:00"
```
Naive string slicing in watchdog extracted the `HH:MM` substring directly without timezone normalization:
```python
# BROKEN: Extracts "01:02" (UTC) instead of local time
end_hm = end_time.replace("T", " ").split(" ", 1)[-1][:5]
if end_hm >= win_end_hm: # Comparing "01:02" >= "08:00" -> False!
    return True
```
Because `"01:02" >= "08:00"` evaluated to `False`, `_is_session_manifest_completed` returned `False`. Consequently, `is_cluster_session_busy` fell back to `global_runner_busy = True`. The watchdog believed Session 1 had not reached the completion boundary and suppressed reporting indefinitely until Session 2 completed hours later.

### 3. The Permanent Fix
Parse the timestamp into timezone-aware datetime and convert to local time (`Asia/Ho_Chi_Minh` / `HCMC`):
```python
try:
    dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(HCMC)
    end_hm = dt.strftime("%H:%M")
except Exception:
    end_hm = end_time.replace("T", " ").split(" ", 1)[-1][:5]
if end_hm >= win_end_hm:
    return True
```
When `end_time` is `"2026-10-13T01:02:39+00:00"`, `dt.astimezone(HCMC)` yields `08:02`, correctly satisfying `"08:02" >= "08:00"`.

---

## Why Latent Bugs Stay Dormant (The Latency Trigger Pattern)

* On days where runs finish ahead of time (e.g. 07:13 or 07:34), `is_feed_runner_active()` drops to `False` during the idle gap between 07:35 and 08:00. The watchdog delivers reports via the idle branch without ever executing the manifest end-time comparison branch.
* The bug only surfaces when run duration stretches past the schedule boundary (e.g. 08:02), triggering concurrent execution with the subsequent session.
* **Lesson:** When verifying multi-session coordination logic, always test boundary overlap cases where Session N finishes AFTER Session N+1 has already spawned.

---

## Row 7/8 Deep Slot Timeout Accumulation

* **Slot Depth Factor:** Rows 7 and 8 occupy deep positions in the TikTok Account Switcher (Slot 7 & 8). They suffer significantly higher rates of session expiration, missing accounts in switcher XML, and focus failures.
* **Timeout Stacking:** When multiple devices fail focus (`prepare-tiktok failed to focus TikTok after launch`), retry backoffs accumulate until hitting the outer watchdog budget:
  `multi-machine-feed-session/watchdog_budget` = 7,200 seconds (2.0 hours).
* **Pool Congestion:** Devices lingering until the 2-hour deadline congest parallel worker pools, starving subsequent machines and forcing the entire batch run to the 2.0-hour ceiling.

---

## Coordinator Dispatch Contract Best Practices

When delegating code-surgery on repos with space in directory names (e.g. `D:/Taadaa/tiktok-luot nuoi acc`):
1. **Avoid Whitespace in `FOCUSED_TEST`:** Guard regexes like `r"^python -m py_compile [^\s]+\.py$"` break on unescaped spaces. Use relative paths within the repo: `python -m py_compile scripts/feed_session_watchdog.py`.
2. **Strict Guard Block Markers:**
   - Always format `OLD_STRING: <<< ... >>>` and `NEW_STRING: <<< ... >>>`.
   - Never wrap file paths with `<<< ... >>>` (the parser treats `<<<` as part of the path, failing absolute path checks).
3. **Instruct Worker on Shell Whitelist:** Worker subagent terminals typically whitelist only `git`, `pytest`, `adb`, and reject inline `python -c`. Instruct the worker directly to use the `patch` tool with `mode='replace'` instead of terminal shell workarounds.
