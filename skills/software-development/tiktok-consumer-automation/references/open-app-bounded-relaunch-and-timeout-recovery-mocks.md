# open_app() Bounded Relaunch and Multi-Stage Mock Invariants

## Context & Problem
In `open_app(device_id)` in `social_reg_v1.py`, TikTok launch has multiple defensive recovery mechanisms during the wait loop (`while time.time() < end`):
1. Immediate Play Store / popup dismiss.
2. In-loop UIAutomator foreground recovery (`com.github.uiautomator.MainActivity` -> force-stop, restart atx stub, HOME, relaunch).
3. Bounded launcher/crash recovery at 12s (`not launch_retry and (time.time() - start_time) >= 12.0`): if TikTok has not reached foreground (device stuck on `com.sec.android.app.launcher` or crash dialog), dismiss crash dialog/unlock keyguard, force-stop, HOME, and relaunch TikTok once.
4. While-else timeout recovery at 45s: if wait expires and `fg_after` shows `com.github.uiautomator.MainActivity`, force-stop uiautomator, restart stub, HOME, and relaunch.

## Predicate Invariant for Bounded Launcher Relaunch
The 12s launcher relaunch predicate must NOT conflate an active UIAutomator stub in foreground with a launcher stall:
```python
crash_detected = any(k in flat_check for k in ["tiktok lien tuc dung lai", "tiktok da dung lai", "tiktok keeps stopping", "dong ung dung", "close app"])
launcher_detected = ("com.sec.android.app.launcher" in fg_check or APP_PACKAGE not in fg_check) and not ("com.github.uiautomator" in fg_check and "MainActivity" in fg_check)
if crash_detected or launcher_detected:
    # Relaunch once, bounded by launch_retry = True
```
This ensures:
- Real launcher and crash dialogs trigger a clean one-shot relaunch.
- If UIAutomator takes the foreground, it is handled by the dedicated UIAutomator recovery path (either in-loop or at timeout), never misclassified as a generic launcher relaunch.

## Test Mock Pitfall: Multi-Stage Launch Counters
When mocking `_launch_tiktok` in unit tests (such as `tests/test_open_app_uiautomator_recovery.py`):
- `launch_count` tracks calls to `_launch_tiktok`.
- Launch 1: Initial launch before wait loop.
- Launch 2: 12s bounded launcher relaunch (if foreground remained launcher during wait).
- Launch 3: UIAutomator timeout recovery relaunch in the `while-else` block.

**Trap:**
If mock responses use `if launch_count[0] >= 2: return TIKTOK_XML` to simulate "success after recovery", the 12s launcher retry will immediately increment `launch_count` to 2. The mock then prematurely returns `TIKTOK_XML` / `SplashActivity`, exiting the loop and preempting the while-else UIAutomator timeout-recovery block under test.

**Fix:**
In timeout-recovery tests where the wait loop is expected to exhaust retries before hitting the `else:` timeout block, calibrate the mock threshold to account for all prior bounded retries (`launch_count[0] >= 3`).
