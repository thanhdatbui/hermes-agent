# Device Soft Reboot Recovery for OPEN_TIKTOK

Introduced: 2026-07-26
Consumer repo: `D:\Taadaa\Tiktok-video`
Target handler: `_handle_open_tiktok` in `scripts/tiktok_workflow/state_machine.py`

## Problem

Some Android farm devices (particularly Samsung S7-series like SM-G930S) occasionally
enter a state where TikTok sticks at SplashActivity even after `am force-stop` + cold
launch. The `ui_retry_limit` (default 3) force-stop→launch→wait-for-feed attempts all
fail, and the workflow escalates to MANUAL_REVIEW — requiring human intervention just
to reboot the device.

A **soft reboot recovery** layer between retry exhaustion and MANUAL_REVIEW can
automatically recover these devices, keeping the workflow running without operator
attention.

## Config Opt-In

The feature is **fail-closed** — it must be explicitly enabled:

```yaml
# config.yaml
allow_device_reboot_recovery: true
```

Default is `False`. The value is passed through `context.config` to the state machine:

```python
# In run_post.py run_real():
context.config = {
    ...
    "allow_device_reboot_recovery": config.allow_device_reboot_recovery,
}
```

## Implementation: `_soft_reboot_recovery`

Added as a method on `StateMachine` in `state_machine.py`. The full 6-step sequence:

```python
def _soft_reboot_recovery(self, adapter, package, feed_indicators) -> bool:
    logger.info("=== SOFT REBOOT RECOVERY ===")
    adb = adapter._adb

    # Step 1/6: adb shell reboot
    result = adb.shell(["reboot"], timeout=5, check=False)
    # -> if not result.ok: return False

    # Step 2/6: adb wait-for-device (120s timeout)
    wait_result = adb.run(["wait-for-device"], timeout=120, check=False)
    # -> if not wait_result.ok: return False

    # Step 3/6: Poll sys.boot_completed=1 (60s)
    boot_deadline = time.time() + 60
    while time.time() < boot_deadline:
        prop_result = adb.shell(["getprop", "sys.boot_completed"],
                                timeout=5, check=False)
        if prop_result.ok and prop_result.stdout.strip() == "1":
            boot_ok = True; break
        time.sleep(2)
    # -> if not boot_ok: return False

    time.sleep(5)  # settle time after boot

    # Step 4/6: am force-stop
    adb.shell(["am", "force-stop", package], timeout=10, check=False)
    time.sleep(2)

    # Step 5/6: Relaunch TikTok
    launch_ok = adapter.launch_app(package)
    # -> if not launch_ok: return False

    # Step 6/6: Wait for feed 30s
    feed_found = self._wait_for_feed(adapter, feed_indicators, timeout=30)
    # -> if feed_found: return True else: return False
```

## Integration in `_handle_open_tiktok`

Inserted right after the for-loop (retry exhaustion) and before the MANUAL_REVIEW block:

```python
    # After the for-loop exhausts all attempts
    allow_reboot = self.context.config.get("allow_device_reboot_recovery", False)
    if allow_reboot:
        logger.warning("3 retries failed → attempting soft reboot recovery ...")
        reboot_ok = self._soft_reboot_recovery(adapter, package, feed_indicators)
        if reboot_ok:
            logger.info("Soft reboot recovery succeeded ✓")
            return True
        logger.error("Soft reboot recovery also failed → MANUAL_REVIEW")

    # Original MANUAL_REVIEW block (unchanged, with enhanced error message)
    self.context.is_ui_unavailable = True
    self.context.error = (
        f"[OPEN_TIKTOK_FAILED] ... "
        f"{'Soft reboot recovery cũng thất bại. ' if allow_reboot else ''}"
        f"Cần MANUAL_REVIEW: ..."
    )
    return False
```

## Logging Convention

Each step is logged with `[REBOOT_N/6]` prefix for grep-ability:

| Step | Tag | Action |
|------|-----|--------|
| 1 | `[REBOOT_1/6]` | Sending reboot command |
| 2 | `[REBOOT_2/6]` | Waiting for device (120s) |
| 3 | `[REBOOT_3/6]` | Waiting for sys.boot_completed=1 |
| 4 | `[REBOOT_4/6]` | Force-stopping TikTok |
| 5 | `[REBOOT_5/6]` | Launching TikTok |
| 6 | `[REBOOT_6/6]` | Waiting for feed (30s) |

## Interaction with Automation-Core

`AdbClient` in automation-core already has:
- `allow_device_reboot_recovery=True` parameter (for its own `_wait_for_device` retry logic)
- Automatic connection retry (`connection_retry_attempts=3`) with `_wait_for_device` between retries
- Connection-loss detection via `_is_connection_lost()`

The consumer's reboot recovery is independent of core's reboot support — the consumer
issues `adb shell reboot` via the `shell()` method, and core's `run()` method automatically
handles reconnection via its own `_wait_for_device()` + retry loop if the ADB daemon
experiences connection loss during `wait-for-device`.

## Pitfalls

1. **`wait-for-device` blocks, may need longer timeout than default (20s).**
   Always pass `timeout=120` explicitly. Farm devices can take 60-90s to reappear.

2. **`wait-for-device` can return before boot completes.**
   The ADB connection is established at the kernel/init stage, before Android's
   `init` process finishes. Always add the `sys.boot_completed` polling loop.

3. **Monkey/am start can race with boot finalization.**
   The 5-second `time.sleep(5)` after `sys.boot_completed=1` is empirical — without it,
   `monkey -p com.ss.android.ugc.trill ...` may fail with "Error: no activities found"
   because the launcher activity isn't yet registered.

4. **AdbClient.run() raises ADBError on timeout,** not returns a result with `ok=False`.
   Wrap both `shell()` and `run()` calls in `try/except Exception` when passing
   timeouts that could be exceeded.

5. **Reboot on a device that's mid-operation (e.g. USB file transfer) can corrupt storage.**
   Only use this as a last-resort recovery when the device is already in a non-functional
   state (can't reach feed despite force-stop+launch). Do NOT reboot healthy devices.
