# Operator Device Lock for Single Machine Actions

## 1. Core Rule & Operator Expectation
When executing ad-hoc investigation, test probes, single-device recovery, or manual runners on Android farm devices, **NEVER interact with devices without an active device lock**.

Un-locked commands risk race conditions with background watchdogs and batch schedulers (`cron_mobiproxy_healer`, `farm_wifi_auto_healer`, `avatar_idle_uploader_watchdog`, feed-session batch runs). Such races can trigger contradictory ADB commands (`input tap`, `svc wifi`, `am start`), invalidate investigation evidence, or crash running live batch sessions.

---

## 2. Standard Pattern: `operator_device_lock`

Use `operator_device_lock` from `automation_core.device_lock`:

```python
from automation_core.device_lock import operator_device_lock
from automation_core.adb import AdbClient

machine_num = "16"
serial = "ce011711201cae2704"

with operator_device_lock(machine=machine_num, serial=serial, project="operator_tool", timeout=30.0) as lease:
    # All ad-hoc ADB commands, preflight verification, and app actions go here
    adb = AdbClient('adb', serial)
    ...
```

### Properties of `operator_device_lock`:
1. **Dual lock creation**: Atomically creates both `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` and `serial_<serial>.lock.json`.
2. **Metadata tracking**: Records process `pid`, `lock_id`, `host`, and timestamp.
3. **Batch safety**: All concurrent batch runners / cronjobs encountering this device will detect the active lock and safely skip it (`SKIPPED_LOCKED`).
4. **Auto-cleanup**: On exit (whether normal completion or unhandled exception), the context manager reliably deletes both lock files.

---

## 3. Pre-Flight Inspection Before Running Ad-hoc Scripts
Before launching single-target batch scripts (such as `run_tiktok_upload_avatar.ps1 -ForceAvatarMachineList 16`), verify device availability via `python D:/Taadaa/tools/inspect_machine.py <N>` to ensure no stale or active runner lock is held by another process.
