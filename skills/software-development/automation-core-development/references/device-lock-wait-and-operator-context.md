# wait_for_device_lock, operator_device_lock, and DeviceLockTimeoutError Patterns

## Scope & Purpose
For scripts, runners, or CLI tools needing cross-project or operator-exclusive device locks with retry/wait behavior:
- `DeviceLockTimeoutError`: Raised when waiting for a lock exceeds `timeout_seconds`. Inherits from `TimeoutError` (or `RuntimeError`).
- `wait_for_device_lock`: Retries `acquire_device_lock` periodically until acquired or timeout expires.
- `operator_device_lock`: Context manager wrapping `wait_for_device_lock` with guaranteed release on exit.

## Public Surface Contract in `automation_core.device_lock`

### 1. `DeviceLockTimeoutError`
```python
class DeviceLockTimeoutError(TimeoutError):
    """Raised when waiting to acquire a device lock times out."""
    def __init__(
        self,
        machine: str | int | None,
        serial: str | None,
        *,
        timeout_seconds: float,
        waited_seconds: float,
        owner: dict | None = None,
        reason: str = "",
    ) -> None:
        self.machine = machine
        self.serial = serial
        self.timeout_seconds = timeout_seconds
        self.waited_seconds = waited_seconds
        self.owner = owner or {}
        self.reason = reason
        msg = (
            f"timed out waiting for device lock after {waited_seconds:.1f}s "
            f"(timeout={timeout_seconds:.1f}s): machine={machine} serial={serial}"
        )
        if self.reason:
            msg += f" reason={self.reason}"
        super().__init__(msg)
```

### 2. `wait_for_device_lock`
```python
def wait_for_device_lock(
    *,
    machine: str | int | None = None,
    serial: str | None = None,
    project: str,
    timeout_seconds: float = 60.0,
    poll_interval: float = 2.0,
    user_authorized: bool = True,
    **acquire_kwargs,
) -> DeviceLockLease:
    """Poll acquire_device_lock until success or timeout_seconds elapsed."""
```
**Key Behaviors**:
- Re-polls on `DeviceLockUnavailable` and `DeviceLockNeedsUserDecision` (when lock is still held by an active process).
- Re-checks process liveness using `_owner_process_alive(owner)`. If owner PID is dead/stale, attempt takeover/clean acquisition on the next loop or let `acquire_device_lock` resolve.
- Avoids zero/negative sleep intervals; clamps `poll_interval` appropriately.
- If deadline expires, raises `DeviceLockTimeoutError` with the last observed owner payload.

### 3. `operator_device_lock`
```python
@contextmanager
def operator_device_lock(
    *,
    machine: str | int | None = None,
    serial: str | None = None,
    project: str,
    timeout_seconds: float = 60.0,
    poll_interval: float = 2.0,
    force_preempt: bool = False,
    **acquire_kwargs,
) -> Iterator[DeviceLockLease]:
    """Context manager acquiring device lock with waiting and fail-safe release."""
    lease = wait_for_device_lock(
        machine=machine,
        serial=serial,
        project=project,
        timeout_seconds=timeout_seconds,
        poll_interval=poll_interval,
        user_authorized=True,
        force_preempt=force_preempt,
        **acquire_kwargs,
    )
    try:
        yield lease
    finally:
        lease.release()
```

### 4. Public Exports
Expose in both:
- `automation_core.device_lock`
- `automation_core/__init__.py` (`__all__` list and top-level imports).

## Testing Strategy
- Test `wait_for_device_lock` immediate acquire when lock is free.
- Test retry & success when lock is released during polling by mock or background thread.
- Test raising `DeviceLockTimeoutError` when lock is held past `timeout_seconds`.
- Test `operator_device_lock` context manager ensures release even if body raises an exception.
- Run tests via:
  ```bash
  PYTHONPATH=src pytest -q tests/test_wait_device_lock.py
  ```
