# Watchdog Hermes Cron Modularization & sys.path Invariants

## Context & Incident Analysis (15/10/2026)

When `feed_session_watchdog.py` was refactored and modularized into sub-packages under `scripts/watchdog/` (`lock.py`, `merger.py`, `alerts.py`, etc.), both the Feed Watchdog and Follow Watchdog cron jobs crashed with:
```text
ModuleNotFoundError: No module named 'watchdog'
```
Root cause:
1. Hermes scheduler runs scripts located in `%LOCALAPPDATA%\hermes\scripts\`.
2. Python sets `sys.path[0]` to the directory containing the executed script.
3. Because the `watchdog/` package only existed inside `D:\Taadaa\tiktok-luot nuoi acc\scripts\`, the script could not resolve `from watchdog.lock import ...`.
4. `follow_session_watchdog.py` imports `feed_session_watchdog`, so crashing feed watchdog instantly broke follow reporting as well.

---

## 1. Mandatory sys.path Bootstrap Pattern

Any script intended for execution by Hermes Cron, Windows Task Scheduler, or external runners MUST bootstrap its search path before importing internal packages:

```python
import os
import sys

_candidate_dirs = [
    os.path.dirname(os.path.abspath(__file__)),
    r"D:\Taadaa\tiktok-luot nuoi acc\scripts",
    r"D:\Taadaa\tiktok-luot nuoi acc",
]
for _d in _candidate_dirs:
    if os.path.isdir(_d) and _d not in sys.path:
        sys.path.insert(0, _d)

# Now safe to import internal packages
from watchdog.lock import ProcessLock, is_feed_runner_active, is_pid_alive
from watchdog.merger import is_device_locked_skip, merge_machine_result, merge_follow_result, merge_upload_result
```

---

## 2. Hermes Cronjob Execution Best Practices

For jobs that rely on repository packages and virtual environments:
- **Direct Prompt Invocation:** Configure the cron job with `prompt` running the repository script directly:
  ```yaml
  prompt: 'Chạy python "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py" và xuất kết quả.'
  workdir: 'D:\Taadaa\tiktok-luot nuoi acc\scripts'
  ```
- **Avoid Orphan Script Copies:** If using `script: ...`, ensure all supporting package files exist in `%LOCALAPPDATA%\hermes\scripts\` or use the `sys.path` bootstrap above.

---

## 3. Dual-File Parity Invariant (Standalone vs Hermes Cron)

The codebase maintains two synchronized copies:
1. `scripts/feed_session_watchdog.py` — Standalone CLI entrypoint.
2. `scripts/hermes_cron/feed_session_watchdog.py` — Hermes background cron runner.

### Rules for Editing:
- Any change to reconcile helpers (`buffer_reconcile_iso`, `parse_reconcile_iso_dt`, `is_session_key_p1_or_unknown`, `RECONCILE_METRICS`) MUST be mirrored identically in both files.
- `test_reconcile_helpers_in_sync_with_hermes_cron` enforces text block equality between `RECONCILE_METRICS: dict` and `def reconcile_cluster_following(`.
- Both files must document their DRY parity relationship in their module docstrings.

---

## 4. Subsecond & Boundary Capping Invariants

When manipulating datetime windows for SQLite log matching:
- **SQLite Format:** Timestamp strings in SQLite are formatted `%Y-%m-%d %H:%M:%S` without subseconds.
- **Microsecond Normalization:** Always set `microsecond=0` on `end_of_day` and `start_of_day`:
  ```python
  end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=0)
  start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
  ```
  Setting `microsecond=999999` and then replacing with `microsecond=0` creates subsecond window drift.
- **Negative Minutes Capping:** Buffer adjustments with `minutes < 0` MUST be clamped to `start_of_day` to prevent date underflow.
- **Telemetry Logging Deduplication:** When logging telemetry on buffer application, ensure that capped events and non-capped events do not fire duplicate log lines:
  ```python
  if was_capped:
      logger.info("[RECONCILE_BUFFER_TELEMETRY] capped boundary iso=%s -> %s (minutes=%d)", iso_val, res, minutes)
  elif minutes != 0:
      logger.info("[RECONCILE_BUFFER_TELEMETRY] iso=%s -> %s (minutes=%d, capped=False)", iso_val, res, minutes)
  ```
