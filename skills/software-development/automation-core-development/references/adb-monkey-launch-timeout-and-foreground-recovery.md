# ADB Monkey Launch Timeout Resilience and Foreground Focus Recovery

## Context & Phenomenon
On real Android device farms (74+ devices), launching apps (e.g. TikTok `com.ss.android.ugc.trill`) via ADB monkey:
```bash
adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1
```
can intermittently hang or exceed the default subprocess timeout (15s) when:
- The device CPU / I/O is saturated (video playback, cache writes, background network sync).
- The target app is already running and in foreground.
- The ADB daemon is momentarily under load.

## Root Cause Mechanics
1. **`AdbClient._execute` Timeout Mechanics:**
   In `automation_core/adb.py`, `adb.shell(..., timeout=timeout, check=False)` catches `subprocess.TimeoutExpired` and raises `ADBError(f"adb command timed out: {cmd_list}")`. Setting `check=False` only prevents exit-code assertions; it does NOT suppress `TimeoutExpired` exceptions.
2. **Crash in `prepare_app_for_automation`:**
   Calling `adb.shell(["monkey", ...], timeout=timeout, check=False)` directly without `try...except Exception` causes unhandled `ADBError` to propagate and abort the entire automation session even when the app is already up and running on screen.

## Critical Downstream Test Invariant (DO NOT Pre-Check & Skip)
- **Pitfall:** An intuitive patch is to check `focus_reader()` before calling monkey, and if `cur_pkg == target`, skip monkey entirely.
- **Why this breaks tests:** Downstream consumer test suites (such as `tiktok-luot nuoi acc/python_runner/tests/test_device_prepare.py`) frequently mock `get_focused_activity` / `focus_reader` returning `target` across the whole lifecycle, and explicitly assert that monkey was dispatched:
  ```python
  self.assertIn(["monkey", "-p", target, "-c", "android.intent.category.LAUNCHER", "1"], calls)
  ```
  Skipping monkey beforehand causes test suite assertion failures.

## Canonical Pattern
1. **Always attempt monkey invocation:**
   - Enforce an increased timeout threshold: `monkey_timeout = max(timeout, 30.0)`.
   - Wrap in `try...except Exception as exc:` to catch `ADBError` / timeout cleanly.
2. **Verify focus upon failure/timeout:**
   - If monkey returned non-zero or threw an exception, immediately query `cur_pkg, cur_act = focus_reader()`.
   - If `cur_pkg == target`, treat the launch as successful (`launch_ok = True`, `launch_error = ""`).
3. **Wrap retry monkey attempts:**
   - Inside verify loops (e.g. attempt 4, 7), wrap monkey retries in `try...except Exception: pass` with `timeout=max(timeout, 30.0)` so transient ADB stalls never terminate the flow.
