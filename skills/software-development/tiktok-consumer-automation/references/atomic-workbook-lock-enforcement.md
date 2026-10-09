# Fallback Workbook Lock Enforcement & Stale Lock TTL

## Background
In TikTok consumer workflows (such as `scripts/tiktok_workflow/account_source.py`), workbook access is guarded by `atomic_workbook_update`. When `automation-core` is dynamically resolved or falls back to an inline implementation, the fallback lock must adhere to strict concurrency guarantees to pass code review and prevent data corruption.

## Key Requirements for Lock Approval

### 1. Stale Lock TTL Recovery
When a worker crashes or is abruptly killed, the lock file (`.lock`) created via `os.open(..., O_CREAT | O_EXCL)` remains on disk. Without TTL detection, all subsequent updates on that workbook will deadlock indefinitely.
- **Rule**: Break stale locks if the lock file's modification time is older than `2 * lock_timeout` (e.g. `(lock_timeout or 30) * 2`).
- **Implementation**:
  ```python
  if lock_file.exists():
      try:
          if time.time() - lock_file.stat().st_mtime > (lock_timeout or 30) * 2:
              lock_file.unlink()
      except OSError:
          pass
  ```

### 2. Fail-Closed Lock Enforcement (`TimeoutError`)
Never fall through into the critical section (editing, backing up, or replacing the workbook) if the lock was not acquired.
- **Anti-Pattern**: Exiting the `while time.monotonic() < deadline:` loop without checking `acquired`, proceeding to modify the workbook unprotected.
- **Correct Pattern**:
  ```python
  if not acquired:
      raise TimeoutError(f"Could not acquire lock on {lock_file} within {lock_timeout}s")
  ```

### Canonical Reference Implementation
```python
def atomic_workbook_update(path, update_cb, backup=True, lock_timeout=30):
    p = Path(path)
    lock_file = p.with_suffix(p.suffix + ".lock")
    deadline = time.monotonic() + (lock_timeout or 30)
    acquired = False
    fd = None
    while time.monotonic() < deadline:
        try:
            # Break stale lock if older than 2x timeout
            if lock_file.exists():
                try:
                    if time.time() - lock_file.stat().st_mtime > (lock_timeout or 30) * 2:
                        lock_file.unlink()
                except OSError:
                    pass
            # Atomic exclusive lock file create
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            acquired = True
            break
        except FileExistsError:
            time.sleep(0.2)
        except Exception:
            break

    if not acquired:
        raise TimeoutError(f"Could not acquire lock on {lock_file} within {lock_timeout}s")

    try:
        # Critical section: backup, modify temp copy, replace original atomically
        ...
    finally:
        if acquired and fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                if lock_file.exists():
                    lock_file.unlink()
            except OSError:
                pass
```

### 3. Concurrent Read-Side Hazard & Hardened Per-Attempt Lock-Wait Pattern
`atomic_workbook_update` guarantees write-side atomicity by replacing the file from a temporary copy. However, standard readers (e.g. `openpyxl.load_workbook(..., read_only=True)`) do not acquire exclusive locks.
- **Symptom**: During heavy batch operations where dozens of workers upload simultaneously, reading workers intermittently fail with `[READ_WORKBOOK_ERROR] Missing required fields: ID TikTok` or openpyxl XML parsing errors / permission denied because the file was being replaced or synced by OneDrive at the exact millisecond of reading.
- **Remedy**: Workbook readers under batch concurrency (`AccountSource.read_row`) must:
  1. Extract lock waiting into a helper `_wait_for_lock(lock_file, timeout=10.0) -> float` returning total seconds waited.
  2. Call `_wait_for_lock()` **inside** the retry loop before every read attempt, so if a lock appears mid-flight between retries, reading waits safely for release.
  3. Track telemetry metrics on the instance (`self._read_attempts`, `self._lock_wait_seconds`).
  4. Emit structured recovery telemetry `[WORKBOOK_READ_RECOVERED]` when read succeeds after retry (`attempt > 1`) or lock wait (`total_lock_wait > 0`).
  5. Ensure workbook handle (`_wb.close()`) is closed on both success and exceptions to avoid leaking open file handles.

```python
# Hardened per-attempt lock-wait & retry pattern (AccountSource.read_row)
def _wait_for_lock(self, lock_file: Path, timeout: float = 10.0) -> float:
    """Wait for active .lock file to be released or stale (>60s). Returns seconds waited."""
    if not lock_file.exists():
        return 0.0
    start_time = time.monotonic()
    deadline = start_time + timeout
    while lock_file.exists() and time.monotonic() < deadline:
        try:
            if time.time() - lock_file.stat().st_mtime > 60:
                lock_file.unlink()
                break
        except OSError:
            pass
        time.sleep(0.2)
    return time.monotonic() - start_time

# Inside read_row():
lock_file = self.workbook_path.with_suffix(self.workbook_path.suffix + ".lock")
max_attempts = 5
last_exc = None
total_lock_wait = 0.0

for attempt in range(1, max_attempts + 1):
    total_lock_wait += self._wait_for_lock(lock_file)
    try:
        row = self._read_row_from_xlsx()
        if self._wb is not None:
            self._wb.close()
            self._wb = None
        self._read_attempts = attempt
        self._lock_wait_seconds = total_lock_wait
        if attempt > 1 or total_lock_wait > 0:
            logger.info(
                f"[WORKBOOK_READ_RECOVERED] machine={self.machine} device={self.device_id} "
                f"succeeded on attempt {attempt}/{max_attempts}, lock_wait={total_lock_wait:.2f}s"
            )
        return row
    except Exception as exc:
        last_exc = exc
        if self._wb is not None:
            try:
                self._wb.close()
            except Exception:
                pass
            self._wb = None
        if attempt < max_attempts:
            backoff = 0.5 * attempt
            logger.warning(f"Đọc workbook lần {attempt}/{max_attempts} thất bại: {exc}. Thử lại sau {backoff}s...")
            time.sleep(backoff)
        else:
            logger.error(f"Không thể đọc workbook sau {max_attempts} lần thử: {exc}")

self._read_attempts = max_attempts
self._lock_wait_seconds = total_lock_wait
```

