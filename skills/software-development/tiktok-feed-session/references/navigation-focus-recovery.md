# Navigation Focus Recovery & Post-Tap Settle Pattern

## Root Cause: "TikTok focus lost after navigation tap: unknown"
On Samsung devices (especially Galaxy J7/A series running Android 8-11 in the device farm), tapping bottom navigation tabs (Home, Profile) or top tabs (Friends, Following, For You) can cause:
1. **WindowManager Animation Lag**: `get_focused_activity` immediately returns `{}` or empty package name (`""` / `unknown`) while the window surface is transitioning.
2. **SystemUI / Launcher Occlusion**: The tap can land near navigation bar edges or trigger Recent Apps (`com.android.systemui`, `com.sec.android.app.launcher`, `com.google.android.apps.nexuslauncher`).

Without recovery, the runner considers TikTok focus lost, logs `SAFETY_FAILED` or `FAIL`, dumps artifacts, and aborts or misclassifies the session.

---

## Standard 2-Tier Recovery Pattern in `calibrate_screens.py`

In `tap_navigation_target`:
```python
post_focus = get_focused_activity(ctx)
post_package = str(post_focus.get("package") or "")
post_activity = post_focus.get("activity")

# 1. Settle delay: nếu focus trả về None/empty, đợi 1.0s rồi query lại
if not post_package:
    time.sleep(1.0)
    post_focus = get_focused_activity(ctx)
    post_package = str(post_focus.get("package") or "")
    post_activity = post_focus.get("activity")

if post_package != expected_package:
    recovered_focus = False
    is_launcher_or_systemui_or_unknown = (
        not post_package
        or post_package in {
            "com.android.systemui",
            "com.sec.android.app.launcher",
            "com.android.launcher",
            "com.android.launcher3",
            "com.google.android.apps.nexuslauncher",
        }
        or "launcher" in post_package.lower()
        or "systemui" in post_package.lower()
    )
    if is_launcher_or_systemui_or_unknown:
        try:
            # Tier 1: KEYCODE_BACK để đóng Recent Apps / overlay
            ctx.adb.shell(["input", "keyevent", "4"], timeout=ctx.timeout("adb_seconds", 15))
            time.sleep(1.2)
            retry_focus = get_focused_activity(ctx)
            retry_pkg = str(retry_focus.get("package") or "")
            
            # Tier 2: Nếu sau BACK vẫn chưa về expected_package, dùng monkey launcher
            if retry_pkg != expected_package:
                ctx.adb.shell(
                    ["monkey", "-p", expected_package, "-c", "android.intent.category.LAUNCHER", "1"],
                    timeout=ctx.timeout("adb_seconds", 15),
                )
                time.sleep(1.2)
                retry_focus = get_focused_activity(ctx)
                retry_pkg = str(retry_focus.get("package") or "")

            if retry_pkg == expected_package:
                recovered_focus = True
                post_focus = retry_focus
                post_package = retry_pkg
                post_activity = retry_focus.get("activity")
                # Log success...
        except Exception as exc:
            # Log failure...
```

---

## Test & Execution Pitfalls

1. **PYTHONPATH for pytest**:
   When running unit tests in `tiktok-luot nuoi acc`, `automation-core` must be included:
   ```bash
   export PYTHONPATH="python_runner:D:/Taadaa/automation-core:$PYTHONPATH" && pytest python_runner/tests/<test_file>.py
   ```

2. **CẤM grep -rn / recursive scan**:
   The repository contains `.ai-runs`, backups, and deep trees. Running `grep -rn` across `python_runner` or root will hit 900s timeout. Always inspect targeted files directly via `read_file` or write focused Python checks.

3. **Canary Invocation**:
   ```bash
   export PATH="/c/Program Files (x86)/xiaowei/tools:$PATH" && powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
