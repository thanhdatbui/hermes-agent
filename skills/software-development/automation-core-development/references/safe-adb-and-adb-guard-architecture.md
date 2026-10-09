# SafeAdb and AdbGuard Architecture Pattern

## Problem & Motivation
In multi-machine / multi-worker phone farm automation, raw calls to `adb` (via `subprocess.run`, `AdbClient`, or scripts) executed without holding an exclusive device lock (`DeviceContext` / `DeviceLock`) lead to concurrency collisions, unexpected screen interruptions, and flakiness across batch jobs and cron tasks.
Crucially, relying on LLM prompt memory alone is insufficient; safety must be enforced at the **code/infrastructure level** with automatic rolling-wait (waiting for active cron jobs to finish without `force_preempt=True`).

## Design Specification

### 1. `SafeAdb` Context & Execution Wrapper (`automation_core.safe_adb`)
- **Exception**: `LockNotHeldError(RuntimeError)` raised if ADB operations are called when the lock is not held.
- **Active Registry**: `_ACTIVE_LOCKED_SERIALS: set[str]` tracking serials currently locked by the process.
- **Context Manager**:
  ```python
  class SafeAdb:
      def __init__(self, serial: str, machine: str | int = "1", project: str = "safe-adb", poll_interval: float = 10.0, **kwargs):
          self.serial = str(serial)
          self.machine = str(machine)
          self.project = project
          self.poll_interval = poll_interval
          self.kwargs = kwargs
          self._lock_held = False

      @contextmanager
      def acquire(self, timeout_seconds: float = 300.0):
          deadline = time.monotonic() + timeout_seconds
          while True:
              try:
                  with DeviceContext(serial=self.serial, machine=self.machine, project=self.project, force_preempt=False, **self.kwargs) as lease:
                      self._lock_held = True
                      _ACTIVE_LOCKED_SERIALS.add(self.serial)
                      try:
                          yield lease
                      finally:
                          self._lock_held = False
                          _ACTIVE_LOCKED_SERIALS.discard(self.serial)
                  break
              except DeviceLockUnavailable as err:
                  remaining = deadline - time.monotonic()
                  if remaining <= 0:
                      raise TimeoutError(f"Timed out waiting for lock on {self.serial} (owner={err.owner})") from err
                  time.sleep(min(self.poll_interval, remaining))
  ```
- **Guarded Execution**:
  Methods `run()` and `shell()` assert `if not self._lock_held: raise LockNotHeldError(...)` before delegating to `AdbClient` or running commands.

### 2. Global Enforcement Hook (`automation_core.adb_guard`)
- **Subprocess Interception**:
  Hooks `subprocess.run` (and `subprocess.Popen`) during test runs or production guard mode.
- When arguments match `adb ... -s <serial> ...`:
  - Extracts target serial.
  - Verifies `<serial> in _ACTIVE_LOCKED_SERIALS`.
  - If not locked, raises `LockNotHeldError("ADB execution on serial %s blocked: device lock not held!")`.
- Provides `install_adb_guard()` and `uninstall_adb_guard()`.

### 3. Coordinator Preflight Lock Check (Anti-Timeout Discipline)
- Before dispatching workers, the Coordinator must check `inspect_device_lock(machine=N)` O(1).
- If the machine is busy, **do not dispatch a blocking worker** (which times out after 600s).
- Instead, alert the user and queue the task for rolling-wait watchdog execution.
