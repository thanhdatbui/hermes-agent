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

## 3. Physical Hard Enforcement: `guard_device_bulkhead.py` & `with_device_lock.py`
From 2026-10-10, lock discipline is physically enforced at the Hermes Pre-tool Hook (`guard_device_bulkhead.py`):
1. **Default-Deny for ADB Device Operations**: Any `adb` command mutating device state (`shell`, `push`, `pull`, `install`, `reboot`, `exec-out`, `logcat`, `tcpip`) without an active lease in `~/.codex/device-locks/` is blocked with `GUARD_DEVICE_LOCK_REQUIRED`.
2. **Compound Command Splitting**: Statements split by `&&`, `||`, `;`, `|`, `&`, `$(...)`, and backticks are evaluated individually. Chaining a benign command (`adb devices && adb -s SERIAL shell ...`) cannot bypass the lock check.
3. **Kernel Anti-Forgery**: Lock validation requires schema protocol v2 AND checks kernel process creation timestamp via `owner_process_alive()` (WinAPI `GetProcessTimes` / `WMIC`). Self-asserted JSON files with fake timestamps are rejected.
4. **CLI Wrapper**: For single commands, use:
   ```bash
   python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>
   ```

---

## 4. Critical Pitfall: Do NOT Wrap Batch Launchers in `operator_device_lock`
Batch runners (`run_tiktok_upload_batch.ps1`, `run_tiktok_upload_avatar.ps1`, `run-feed-session.ps1`) **already implement their own device lock lifecycle** (`machine_inventory` admission check -> `acquire_device_lock`).

- **Trap**: If an operator or coordinator wraps a batch script call inside an external `with operator_device_lock(machine=N, ...)` context:
  `machine_inventory` checks `~/.codex/device-locks/machine_<N>.lock.json`, sees the external lock, and marks the machine as `SKIPPED_LOCKED: device lock active` (exit=3, verified=False).
- **Correct Pattern**:
  - For ad-hoc single Python/ADB probe commands: Bọc qua `operator_device_lock` hoặc `with_device_lock.py`.
  - For full batch scripts: Chạy trực tiếp batch launcher (chạy background với `timeout > 60s`), để launcher tự acquire lock.
  - If a machine is currently locked by a running batch (e.g. `multi-machine-feed-session`), do not disrupt or force execution; wait for the existing batch to release the lock cleanly before launching.
