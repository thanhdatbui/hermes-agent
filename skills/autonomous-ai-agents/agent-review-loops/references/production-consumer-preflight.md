# Production Consumer Preflight

Use this after reviewer `APPROVED` and before any live device action. A reviewer verdict is tied to a workspace snapshot; real production data can reveal additional schema/runtime mismatches.

## Workbook checks

1. Open the actual workflow workbook, not only a fixture.
2. Read the real header row and canonicalize aliases such as `ID` → `ID TikTok`.
3. Select the first row for the requested machine and reject blank/whitespace serials.
4. Treat Excel numeric folder cells safely: `489` and `489.0` must resolve to folder `489`.
5. Compute `next_video = Video Đã Đăng + 1`; verify the exact source file exists.
6. Confirm the configured workflow workbook is the source of truth for that workflow; do not substitute a different mapping workbook.

## Device and lock checks

1. Resolve the configured ADB executable from the working sibling/project config.
2. Run `adb -s <serial> get-state` and confirm `device`.
3. Check both machine and serial lock files; never delete a live owner lock.
4. **Acquire the device lock before any manual ADB operation** (dumpsys, UI dump, screenshot). Not acquiring it risks interference from parallel runners on the same device pool.
5. Keep preflight read-only: no TikTok launch, media push, workbook write, or post.

## Startup/failure checks

1. The live state sequence must be `ACQUIRE_LOCKS → CONNECT_DEVICE/PREPARE_DEVICE → OPEN_TIKTOK → DISMISS_POPUPS → ACCOUNT_SWITCHER → DISMISS_POPUPS_AFTER_SWITCH → ACCOUNT_READY`.
2. `automation_core.prepare_device()` must wake, attempt non-credential swipe unlock, lock/verify rotation, and run before TikTok-specific actions.
3. **Device locked/unlock gate**: `automation_core.prepare_device()` returns `locked_or_secure` as diagnostic state after swipe. On devices with swipe-only unlock (no PIN/password), the consumer MUST NOT block on `locked_or_secure` — core already attempted wake+swipe, and `locked_or_secure` alone is not evidence of a real credential lock. Only rotation verification failure (`rotation_locked is not True`) should stop the flow before `OPEN_TIKTOK`. The user explicitly rejects false-positive guards that block devices with swipe-only lockscreens.
4. **Consumer-side swipe retry**: If `prepare_device` returns `locked_or_secure`, the consumer should retry swipe-unlock 3 times with stronger parameters (95%→25% height, 500ms duration) before declaring MANUAL_REVIEW. Verify unlock state using `adb shell dumpsys window policy`, matching only `mShowingLockscreen=true` or `isStatusBarKeyguard=true` — NOT generic `Keyguard=true` or `deviceHasKeyguard=true` (those are capability flags, not lock indicators).
5. **Soft reboot recovery**: If force-stop + relaunch + feed verification fails 3 times and `allow_device_reboot_recovery` is enabled, attempt the full 6-step sequence before MANUAL_REVIEW:
   ```
   1. adb shell reboot
   2. adb wait-for-device (120s timeout)
   3. Poll sys.boot_completed=1 via getprop (60s timeout)
   4. am force-stop TikTok
   5. Launch TikTok (monkey -p / am start)
   6. Wait for feed indicators (30s timeout)
   ```
6. **Feed verification indicators**: After launching TikTok, poll UI dump every 2s for up to 30s looking for: `for you`, `following`, `đề xuất`, `home_tab`, `for_you_tab`. If none found within timeout, treat as launch failure.
7. On any failed/manual run, verify workbook unchanged, remote media absent, and machine/serial leases released or confirmed stale before retry.
8. Before retrying live after a MANUAL_REVIEW: clear old run artifacts (`rm -rf runtime/runs/*`), delete `__pycache__/*.pyc`, and start from a fresh INIT (no stale checkpoints).

## Common pitfalls

- `adb shell dumpsys window policy` may contain `Keyguard=true` or `deviceHasKeyguard=true` even when the device is fully unlocked — these are device CAPABILITY flags, not lock indicators. Only `mShowingLockscreen=true` and `isStatusBarKeyguard=true` mean the device is actually locked.
- If TikTok stays on `SplashActivity` after launch, the app installation may be broken (missing MAIN activity). Check with `pm resolve-activity --brief <package>`.
- When manually testing ADB commands before or during a live run, ALWAYS acquire the device lock first to prevent parallel runner interference.

## Evidence

Record the actual workbook path, machine, serial, next video, ADB state, lock status, runtime report, and whether any side effect occurred. Do not claim live readiness from unit tests alone.
