# Rotation-preparation timeout in feed sessions

## Incident pattern

A `multi-machine-feed-session` alert shows TikTok still healthy on the feed while the worker stops during startup preparation. The signature can be:

```text
adb command timed out: ('C:\Program Files (x86)\xiaowei\tools\adb.exe', '-s', '<serial>', 'shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0')
```
or historically (2026-08-23):
```text
adb command timed out: ... 'shell', 'content', 'insert', '--uri', 'content://settings/system', '--bind', 'name:s:accelerometer_rotation', '--bind', 'value:i:0'
```

This is a **preparation/control-path failure**, not a feed blocker, account failure, CAPTCHA, or TikTok foreground loss.

## Root causes

### 1. Legacy `content insert` hang (2026-08-23)
Commit `594ba5a` added a secondary Samsung/OneUI workaround after `settings put` writes using `content insert`. On S7 (OneUI), this hung until ADB timeout.

### 2. ADB `settings put/get` Timeout & Uncaught Exception (2026-09-05 - Máy 21, Nick lieumiyy3oa)
Under farm load or sluggish ADB daemon, even canonical `settings put` / `settings get` can take > 8-15s or raise `ADBError("adb command timed out: ...")`.
Without an Exception Guard and Timeout Guard inside `ensure_portrait_rotation` and `lock_portrait_rotation`, `AdbClient.shell()` raised an uncaught exception, which propagated out of startup preparation and terminated the feed session erroneously.

## Confirmed fix & Safe implementation contract

1. **Timeout Clamping (Timeout Guard):**
   - In `ensure_portrait_rotation` (`device_prepare.py`):
     `timeout = min(ctx.timeout("adb_seconds", 15), 8.0)`
   - In `lock_portrait_rotation` (`automation_core/startup.py`):
     `effective_timeout = min(timeout, 8.0)`
2. **Exception Isolation (Exception Guard):**
   - Wrap each `settings put` and `settings get` loop in `try...except Exception as exc:`.
   - On error: record `observed[f"{setting}_put"] = "failed"` (or `observed[setting] = "failed"`), append `f"{setting} ... timeout/error: {exc}"` to `errors`.
   - **Never let ADB timeout or ADBError propagate out as an uncaught exception** to abort the feed session.
3. **Symmetrical updates:**
   - Always patch both files together:
     * `python_runner/flows/device_prepare.py` (`ensure_portrait_rotation`)
     * `automation-core/src/automation_core/startup.py` (`lock_portrait_rotation`)
4. **Focused Unit Testing (<5s):**
   - Do NOT run full `test_device_prepare.py` (runs 25 tests with sleep delays, taking ~113s).
   - Use `-k` filter:
     ```bash
     python -m pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_device_prepare.py" -k "ensure_portrait_rotation"
     # Runs in ~3s
     python -m pytest "D:/Taadaa/automation-core/tests/test_startup.py"
     # Runs in ~2s
     ```

## Diagnosis checklist

1. Alert text: `adb command timed out` on `settings put/get` or `content insert` for `accelerometer_rotation` or `user_rotation`.
2. Machine screenshot: TikTok feed tab healthy — NOT CAPTCHA/popup/launcher.
3. Check both `device_prepare.py` and `automation-core/startup.py`.
4. Ensure both have the `min(timeout, 8.0)` cap and `try...except Exception` guard.
5. Verify offline with focused unit tests (`-k ensure_portrait_rotation`). Do not run live retry unless authorized.
