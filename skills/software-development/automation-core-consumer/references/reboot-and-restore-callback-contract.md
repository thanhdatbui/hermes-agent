# reboot_and_restore Callback Contract (automation-core >= 0.2.40)

## The API Change

`soft_reboot_and_wait(adb, serial=..., boot_timeout=..., proxy_timeout=...)` was **removed**.
It was replaced by `reboot_and_restore()` with a completely different signature.

## Current API

```python
from automation_core.device_recovery import reboot_and_restore, prepare_device, wait_until_unlocked

PostRebootCallback = Callable[[], object]  # ZERO arguments

reboot_and_restore(
    adb,                              # AdbClient instance
    *,
    cleanup_before_reboot: PostRebootCallback,    # REQUIRED
    recover_post_reboot: PostRebootCallback,      # REQUIRED
    verify_post_reboot: PostRebootCallback,       # REQUIRED
    recovery_packages: tuple[str, ...] = (),
    force_stop_attempts: int = 2,
    recover_adb_after_reboot: PostRebootCallback | None = None,
    boot_timeout: float = 180,
    verification_timeout: float = 120,
    poll_interval: float = 2,
) -> DeviceReadiness
```

## The Critical Pitfall

All callbacks are `Callable[[], object]` — **zero arguments**. The `adb` client must be captured via closure.

### WRONG (passes adb as argument to callback):
```python
reboot_and_restore(
    adb,
    cleanup_before_reboot=lambda a: None,              # TypeError!
    recover_post_reboot=lambda a: wait_until_unlocked(a),  # TypeError!
    verify_post_reboot=lambda a: prepare_device(a),    # TypeError!
)
# Error: TypeError: <lambda>() missing 1 required positional argument: 'a'
```

### RIGHT (captures adb via closure):
```python
reboot_and_restore(
    adb,
    cleanup_before_reboot=lambda: None,
    recover_post_reboot=lambda: wait_until_unlocked(adb),
    verify_post_reboot=lambda: prepare_device(adb),
    boot_timeout=180,
)
```

## Minimal Consumer Wrapper

```python
from automation_core.adb import AdbClient
from automation_core.device_recovery import reboot_and_restore, prepare_device, wait_until_unlocked

def _soft_reboot(adb_path: Path, serial: str) -> None:
    adb = AdbClient(str(adb_path), serial, default_timeout=20)
    reboot_and_restore(
        adb,
        cleanup_before_reboot=lambda: None,
        recover_post_reboot=lambda: wait_until_unlocked(adb),
        verify_post_reboot=lambda: prepare_device(adb),
        boot_timeout=180,
    )
```

## How to Detect the Import Error

```
ImportError: cannot import name 'soft_reboot_and_wait' from 'automation_core.device_recovery'
```

This means the consumer was written against an older automation-core version. Update the import and adapt to the new callback-based API.
