# ADB Timeout & Foreground Check Guards in Startup Orchestration

## 1. ADB Transport Timeout Behavior (`AdbClient`)
- In `automation_core.adb.AdbClient._execute`, when a command exceeds its timeout (`subprocess.TimeoutExpired`), it raises `ADBError(f"adb command timed out: ...")`.
- **Critical:** This exception is raised **even when `check=False`** is passed to `adb.shell(...)` or `adb.run(...)`. `check=False` only prevents exceptions on non-zero exit codes; it does NOT suppress transport timeouts.
- Any orchestration step calling `adb.shell` for long-running or variable-latency commands (especially `monkey`, `am start`, or UI dumps) must wrap the execution in `try ... except (ADBError, Exception):` to avoid aborting startup unexpectedly.

## 2. Robust App Launch Pattern in `prepare_app_for_automation`
Launching apps on busy Android devices (e.g., Samsung Galaxy S7 farm devices under high CPU load) frequently causes `monkey` execution to take longer than default 15-second timeouts.

### Recommended Defense:
1. **Elevate Launch Timeout:**
   Ensure launch timeout is at least 30s:
   ```python
   launch_timeout = max(timeout, 30.0)
   ```
2. **Foreground Pre-Check:**
   Query `cur_pkg, cur_act = focus_reader()`. If `cur_pkg == target`, the app is already in the foreground, allowing redundant launch calls to be avoided or recorded immediately.
3. **Reconciliation on Exception / Timeout:**
   If `monkey` times out or fails:
   ```python
   try:
       launched = adb.shell(
           ["monkey", "-p", target, "-c", "android.intent.category.LAUNCHER", "1"],
           timeout=launch_timeout,
           check=False,
       )
       launched_ok = launched.ok
       launch_error = "" if launched_ok else (_text(launched.stderr).strip() or "adb command failed")
   except Exception as exc:
       launched_ok = False
       launch_error = str(exc)

   if not launched_ok:
       post_pkg, _ = focus_reader()
       if post_pkg == target:
           launched_ok = True
           launch_error = ""
   ```
4. **Retry Guards inside Poll Loop:**
   Secondary monkey retries inside focus polling loops (e.g. at attempts 4 and 7) must also be wrapped in `try ... except Exception:` so transient timeouts do not abort remaining verification attempts.

## 3. Unit Test Assertions & Mocked `focus_reader` Pitfalls
- In `automation-core/tests/test_startup.py`, tests such as `test_app_startup_default_uses_sixty_second_ui_wait` pass a static lambda:
  `focus_reader=lambda: ("com.example.target", "MainActivity")`
  and assert call counts on `adb.timeouts` (e.g. `assert adb.timeouts == [60, 60]`).
- If an unconditional pre-check bypasses monkey when `focus_reader() == target`, tests using static mock readers will record fewer `adb.shell` calls than expected. Ensure fallback and launch sequencing preserves expected contract steps.

## 4. Avoiding Grep/Find Timeouts across Farm Repos
- Do NOT run recursive searches (`grep -rn`, `find`) across `/d/Taadaa/*` or root repos containing `.ai-runs`, `runs`, or `runtime`.
- Target exact code subdirectories only (e.g. `src/automation_core`, `python_runner/core/`, `tests/`).
