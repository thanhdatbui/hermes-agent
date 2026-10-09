# Device Lock Release On Terminal & AUTOMATION_CORE_RELEASE_ON_FAIL

## Overview
By default, automation runs should not leave dead lock files behind when a run fails or encounters an unhandled exception. In `src/automation_core/device_lock.py`, device lock release behavior on terminal failure is governed by `AUTOMATION_CORE_RELEASE_ON_FAIL`.

## Environment Variable & Helper (Strict Truthy Check)
```python
def _default_release_on_terminal() -> bool:
    raw = os.environ.get("AUTOMATION_CORE_RELEASE_ON_FAIL", "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}
```
- **Default value**: `"1"` -> True (auto-release device locks on failure/exit).
- **Strict truthy check**: Empty string `""` or any unrecognized value returns `False` to prevent accidental unlinking. Only `"1"`, `"true"`, `"yes"`, `"on"` enable auto-release.

## Implementation Details

### 1. `DeviceLockLease`
- Field: `release_on_terminal: bool | None = None`
- In `__post_init__`: If `self.release_on_terminal is None`, resolve via `_default_release_on_terminal()`.
- On `finish(succeeded=False, failure_status=...)`: If `succeeded or self.release_on_terminal`, calls `self.release()`.
- On `__exit__`: If `self.release_on_terminal`, wraps `self.release()` in `try/except (OSError, DeviceLockReleaseError)`:
  - If `exc_type is None`, re-raise so release errors are not silently swallowed on clean exits.
  - If `exc is not None`, log warning and attach `exc.add_note()` to preserve the original exception without masking it.

### 2. `acquire_device_lock`
- Parameter: `release_on_terminal: bool | None = None`
- If `release_on_terminal is None`: resolves to `_default_release_on_terminal()`.
- Passes the resolved boolean to `DeviceLockLease` and `_UnlockedDeviceLockLease`.

### 3. `DeviceLock` Compatibility Adapter
- `__init__`: `release_on_terminal: bool | None = None`, resolved to `bool(_default_release_on_terminal())` when `None`.
- **`lock_path` Property**: Legacy tests and callers access `lock.lock_path`:
  ```python
  @property
  def lock_path(self) -> Path:
      return self.paths[0]
  ```
- **Module-level `_LOCK_DIR`**: Expose `_LOCK_DIR = DEFAULT_LOCK_ROOT` at module level and resolve roots via:
  ```python
  root = Path(lock_root or os.environ.get("CODEX_DEVICE_LOCK_DIR") or _LOCK_DIR)
  ```
  This allows tests to use `monkeypatch.setattr(device_lock, "_LOCK_DIR", tmp_path)` cleanly.
- **Guaranteed Lease Cleanup in `release()`**:
  ```python
  def release(self) -> None:
      try:
          if self.lease is not None:
              self.lease.release()
      finally:
          self.lease = None
          self.acquired.clear()
  ```
- **Synchronized Status Guard & Safe State Resync in `finish()` (Crucial `ambient_exc` & Opt-Out Retention Pitfalls)**:
  *Pitfall 1 (Ambient Exception)*: Inside an `except` block in Python, `sys.exc_info()[1]` returns the exception currently being handled (`exc`). Therefore, `if sys.exc_info()[1] is None:` inside an `except` block will NEVER evaluate to `True`, silently swallowing release failures during normal (non-exception) execution. To properly detect whether the caller was already handling an active exception, capture `ambient_exc = sys.exc_info()[1]` **BEFORE** entering the `try` block.
  *Pitfall 2 (Opt-Out Retention Bookkeeping)*: Do NOT unconditionally clear `self.lease = None; self.acquired.clear()` in a `finally` block. When opt-out retention (`release_on_terminal=False`) applies, `lease.finish()` updates status and retains the lock file on disk. Unconditionally setting `self.lease = None` leaves `lock.status` stale and orphans the lock file. Instead, check `if self.lease.is_still_held()`:
  ```python
  def finish(self, *, succeeded: bool, failure_status: str = "handoff") -> None:
      """Apply the shared success-or-handoff lifecycle to legacy callers."""
      if self.lease is None:
          return
      if not succeeded and self.status in {"recovery", "handoff", "blocked"}:
          return
      ambient_exc = sys.exc_info()[1]
      try:
          if self.lease is not None:
              self.lease.finish(succeeded=succeeded, failure_status=failure_status)
      except (OSError, DeviceLockReleaseError) as exc:
          log.warning("device lock release failed in finish: %s", exc)
          if ambient_exc is None:
              raise
          return
      if self.lease.is_still_held():          # opt-out retention
          self.status = failure_status
          self.payload["status"] = failure_status
      else:                                   # released cleanly
          self.lease = None
          self.acquired.clear()
  ```
- **Safe Release in `__exit__()` (Preserve Original Exception on Windows `OSError`)**:
  ```python
  def __exit__(self, exc_type, exc, tb) -> None:
      if self.lease is None or self.status in {"recovery", "handoff", "blocked"}:
          return
      if self.release_on_terminal:
          try:
              self.release()
          except (OSError, DeviceLockReleaseError) as release_error:
              log.warning("device lock release failed in __exit__: %s", release_error)
              if exc_type is None:
                  raise
              if exc is not None:
                  try:
                      exc.add_note(f"device lock release failed: {release_error}")
                  except AttributeError:
                      pass
          return
      try:
          self.set_status("handoff")
      except DeviceLockStatusError as status_error:
          if exc_type is None:
              raise
          if exc is not None:
              try:
                  exc.add_note(f"device lock handoff persistence failed: {status_error}")
              except AttributeError:
                  pass
  ```
  *Rule*: If an exception occurred inside the `with` block (`exc_type is not None`), catching `(OSError, DeviceLockReleaseError)` and adding a note prevents Python from replacing the original exception with the release failure. If the block exited cleanly (`exc_type is None`), re-raise so unlink failures are not silently swallowed.

## Test Suite Isolation Pattern
The test suite in `tests/test_device_lock.py` exercises handoff status persistence, atomic alias takeover, cross-process recovery contention, and audit logs that expect failed locks to remain on disk in `handoff` status.

When `AUTOMATION_CORE_RELEASE_ON_FAIL` defaults to `"1"`, these handoff tests fail because the lock files are unlinked on terminal failure.

### Solution:
1. In `tests/test_device_lock.py`: add an autouse monkeypatch fixture to isolate takeover/handoff tests from the auto-release default:
```python
@pytest.fixture(autouse=True)
def _isolate_device_lock_env(monkeypatch):
    monkeypatch.setenv("AUTOMATION_CORE_RELEASE_ON_FAIL", "0")
```
2. In `tests/test_release_on_terminal.py`: isolate from any outer environment variables:
```python
@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, ready_root: Path) -> None:
    monkeypatch.setenv("CODEX_DEVICE_READINESS_DIR", str(ready_root))
    monkeypatch.delenv("AUTOMATION_CORE_RELEASE_ON_FAIL", raising=False)
```

### Key Verification Cases:
1. Default behavior (`AUTOMATION_CORE_RELEASE_ON_FAIL` unset / `"1"`): lock file deleted on failure and context exception.
2. Opt-out behavior (`AUTOMATION_CORE_RELEASE_ON_FAIL="0"` or `release_on_terminal=False`): lock retained as handoff.
3. Strict truthy parsing: empty string `""` or invalid values default to retain (`False`).
4. Status Guard: `DeviceLock(status="handoff"|"recovery"|"blocked")` MUST NOT release lock file when `finish(succeeded=False)` or `__exit__` runs with `release_on_terminal=True`.
5. Windows unlink failure safety: When `Path.unlink` or `release()` throws `OSError` on Windows in `__exit__`, it logs a warning and ensures the original exception from the `with` block is re-raised intact without being masked.
6. Ambient exception preservation in `finish()`: If `release()` fails with `OSError` without an ambient exception from the caller, `finish()` raises the `OSError`. If an ambient exception already exists, `finish()` suppresses the secondary release error to avoid masking the primary failure.
7. Opt-out retention on `DeviceLock` wrapper: When `release_on_terminal=False` and status is non-terminal (e.g. `running`), `finish(succeeded=False)` retains the lock file on disk, resyncs `lock.status` and `lock.payload["status"]` to `failure_status`, and preserves `lock.lease` (not None).
