# Rotation-preparation timeout in feed sessions

## Incident pattern

A `multi-machine-feed-session` alert shows TikTok still healthy on the feed while the worker stops during startup preparation. The meaningful signature is:

```text
adb command timed out: ('C:\Program Files (x86)\xiaowei\tools\adb.exe', '-s', '<serial>', 'shell', 'content', 'insert', '--uri', 'content://settings/system', '--bind', 'name:s:accelerometer_rotation', '--bind', 'value:i:0')
```

This is a **preparation/control-path failure**, not a feed blocker, account failure, CAPTCHA, or TikTok foreground loss.

## Root cause (confirmed 2026-08-23)

Commit `594ba5a` (2026-08-19) added a secondary Samsung/OneUI workaround after the canonical `settings put` writes:

```python
ctx.adb.shell([
    "content", "insert", "--uri", "content://settings/system",
    "--bind", f"name:s:{setting}", "--bind", "value:i:0"
], timeout=timeout)
```

On Samsung Galaxy S7 (OneUI), this command hangs until ADB timeout (15 s default). `AdbClient.shell()` raises `ADBError("adb command timed out: ...")` which propagates uncaught out of `ensure_portrait_rotation`. The outer `except Exception` in `_run_child` records the child as `failed` — even though TikTok is on a healthy feed.

The same pattern existed in `automation-core/src/automation_core/startup.py::lock_portrait_rotation`.

## Confirmed fix

Removed `content insert` from both files:

| File | Function | Commit |
|------|----------|--------|
| `python_runner/flows/device_prepare.py` | `ensure_portrait_rotation` | `6bf8f52` (consumer repo) |
| `automation-core/src/automation_core/startup.py` | `lock_portrait_rotation` | `48ed1ee` (automation-core) |

`settings put system accelerometer_rotation 0` + `settings put system user_rotation 0` are sufficient. Standard Android since API 17, never hang.

## Safe implementation contract

1. Use only `settings put system accelerometer_rotation 0` and `settings put system user_rotation 0`.
2. **Do NOT add `content insert --uri content://settings/system`** — hangs on S7/OneUI.
3. If a vendor workaround is ever required: bounded try/except, catch `ADBError`, record distinct evidence field, never let it propagate as session-killing exception.
4. Verify with `settings get` reads after `sleep(0.3)`. Viewport (`wm size`) for deeper confirmation.
5. **Always patch both files together** — consumer `device_prepare.py` AND `automation-core/startup.py`.

## Diagnosis checklist

1. Alert text: `adb command timed out` on `shell content insert ... accelerometer_rotation`.
2. Machine screenshot: TikTok feed tab (Đề xuất), healthy — NOT CAPTCHA/popup/launcher.
3. `git blame` rotation helper → confirm `content insert` was added after original code.
4. Check `automation-core/startup.py::lock_portrait_rotation` — same pattern likely present.
5. Patch both, run regression tests, compile+diff-check, commit+push both repos.
6. Do NOT rerun the live machine to validate — fix is offline-verifiable.

## Regression tests (post-fix baseline)

```bash
# Consumer repo
cd 'D:/Taadaa/tiktok-luot nuoi acc'
PYTHONPATH=python_runner python -B -m pytest -q -p no:cacheprovider python_runner/tests/test_device_prepare.py
# Expected: 23 passed

# automation-core
cd 'D:/Taadaa/automation-core'
python -B -m pytest -q -p no:cacheprovider tests/test_startup.py tests/test_device_readiness.py
# Expected: 15 passed
```

Pre-existing failures to exclude (fail on clean HEAD, unrelated to rotation):
- `test_feed_swipe_smoke.py::test_flow_stops_manual_needed_before_navigation`
- `test_feed_swipe_smoke.py::test_flow_stops_on_focus_loss_before_navigation`

Both fail due to `Mock.stdout` type mismatch in `parse_focused_activity`, not rotation logic.

## Operational boundary

Preserve target screen and lock per farm policy. Do not probe, rerun, force-stop TikTok, return Home, or apply live rotation repair without explicit user authorization. A healthy TikTok feed in the alert screenshot must not be used to dismiss the earlier preparation failure.
