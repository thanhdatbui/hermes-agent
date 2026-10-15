# Monolith Haiku Worker & Import Fallback Patterns (2026-10-15)

## 1. Background
During the refactoring of two massive farm monoliths:
1. `D:/Taadaa/Tiktok-video/scripts/download_by_niche.py` (1.936 -> 1.352 lines, commit acb8e11)
2. `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py` (2.088 -> 1.373 lines, commit 03e3216, 5 modules: lock, merger, alerts, formatters, parser; 55/55 tests passing)

Key systemic failure patterns and their solutions were identified.

## 2. Failure Pattern: Script Import Path Collision
### Symptom
When extracting `scripts/watchdog/lock.py` from `scripts/feed_session_watchdog.py`:
- `pytest tests/test_feed_session_watchdog.py` fails with:
  `ModuleNotFoundError: No module named 'scripts.watchdog'`
  because the test runner executes `sys.path.insert(0, ".../scripts")`. To Python, `watchdog` is at the root of `sys.path`, not `scripts.watchdog`.
- Conversely, running from another repository or outer script might import `scripts.feed_session_watchdog`, where `scripts` is top-level.

### Solution: Dual-Path Import Fallback
In the orchestrator script:
```python
try:
    from watchdog.lock import ProcessLock, is_feed_runner_active, is_pid_alive
    from watchdog.merger import is_device_locked_skip, merge_machine_result
except ImportError:
    from scripts.watchdog.lock import ProcessLock, is_feed_runner_active, is_pid_alive
    from scripts.watchdog.merger import is_device_locked_skip, merge_machine_result
```
In test files:
```python
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))
try:
    from watchdog.lock import ProcessLock
except ImportError:
    from scripts.watchdog.lock import ProcessLock
```

## 3. Failure Pattern: Haiku Worker Multi-Turn Exhaustion (`max_turns=6`)
### Symptom
When asking Haiku worker to perform multi-site modifications in a 2.000-line monolith (e.g. "update imports at top AND delete function A at line 300 AND delete function B at line 900"), the agent spends turns reading large context slices, exhausting `--max-turns 6`:
`Error: Reached max turns (6)`

### Solution: Single-Hunk Atomic Contracting
1. Do not bundle disparate deletions across 1.000 lines into one prompt.
2. Delegate strictly one hunk at a time:
   - Turn 1: Extract module to `scripts/watchdog/<name>.py`.
   - Turn 2: Add import block at top of monolith.
   - Turn 3: Delete local definition of target function block.
3. If an edit must span multiple locations, raise `--max-turns 12` and run as a background task (`terminal(background=True, notify_on_complete=True)`) to respect the host's 60s foreground command ceiling (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).

## 4. Failure Pattern: Closeout Gate `DIFF_TOO_LARGE` (>30 KB)
### Symptom
Running `closeout_gate.py` on a complete refactoring commit touching 11 files with 1.006 additions and 669 deletions (76 KB diff) triggers:
`[Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (76137 > 30000 bytes)`

### Solution
- Refactoring tasks must commit incrementally per thin-slice (e.g., Commit 1: proxy module, Commit 2: dedup module).
- Each commit stays below 25 KB diff, ensuring compliance with the Closeout Gate limit without requiring manual bypasses.
