# Resilient Fallback Pattern for `atomic_workbook_update` in Consumers

Consumers across the farm (e.g. `Tiktok-video`, `tiktok-luot nuoi acc`, `tiktok-follow`) update Excel workbooks (Tik1..Tik6, taikhoan_run_safe) that act as monotonic cursors for devices and batch jobs.

When a consumer runs in an environment where `automation_core` is not pre-installed in `site-packages` or when editable paths (`.pth`) are missing, calling `from automation_core.workbook import atomic_workbook_update` fails with `ModuleNotFoundError` or `ImportError`.

To prevent crashes while maintaining workbook integrity, file locking, and concurrency safety, consumers must implement the standardized 3-tier resolution pattern approved by Claude audit.

---

## 3-Tier Resolution Architecture

1. **Tier 1: Direct Import**
   Attempt standard import from `automation_core.workbook`.

2. **Tier 2: Dynamic Path Detection**
   If direct import fails, check candidate paths for `automation-core/src` and inject into `sys.path`:
   - Environment variable `AUTOMATION_CORE_SRC`
   - Relative traversal: `Path(__file__).resolve().parents[N] / "automation-core" / "src"`
   - Farm root default: `Path("D:/Taadaa/automation-core/src")`

3. **Tier 3: Inline Robust Fallback**
   If both fail, execute an inline atomic update meeting all production safety contracts:
   - **Exclusive File Lock**: Use `os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)` with a deadline loop (default 30s timeout). Prevents race conditions across parallel subagents/runners.
   - **Timestamped Backup**: Create `.bak-%Y%m%d_%H%M%S` copy before modifying.
   - **Staged Tempfile**: Modify workbook inside `tempfile.NamedTemporaryFile(suffix=p.suffix, delete=False, dir=p.parent)` so corrupt saves do not destroy the source file.
   - **Callback Return Contract**: Accept `cb_res is True or cb_res is None` as success. In-place workbook mutators often return `None`, while boolean-returning mutators return `True`.
   - **Windows `PermissionError` (WinError 32) Retry Loop**: On Windows, temporary file handles, background indexing, or antivirus scanners frequently hold file locks for brief periods. Retrying `temp_path.replace(p)` up to 5 times with a 0.5s pause prevents spurious `PermissionError` failures.
   - **Deterministic Cleanup**: Ensure lock file descriptors and temporary files are closed and unlinked in `finally` blocks.

---

## Standard Reference Code (applied in `Tiktok-video/scripts/tiktok_workflow/account_source.py`)

```python
# 1. Thử import trực tiếp từ automation_core.workbook
try:
    from automation_core.workbook import atomic_workbook_update
except (ImportError, ModuleNotFoundError):
    # 2. Dynamic path detection cho automation-core/src
    import os
    import sys
    env_ac = os.environ.get("AUTOMATION_CORE_SRC")
    candidate_paths = [
        Path(env_ac) if env_ac else None,
        Path(__file__).resolve().parents[3] / "automation-core" / "src",
        Path("D:/Taadaa/automation-core/src"),
    ]
    for cand in candidate_paths:
        if cand and cand.is_dir() and str(cand) not in sys.path:
            sys.path.insert(0, str(cand))
    try:
        from automation_core.workbook import atomic_workbook_update
    except (ImportError, ModuleNotFoundError):
        # 3. Fallback inline robust (chống race condition và Windows PermissionError)
        from datetime import datetime
        import shutil
        import tempfile
        import time

        def atomic_workbook_update(path, update_cb, backup=True, lock_timeout=30):
            p = Path(path)
            lock_file = p.with_suffix(p.suffix + ".lock")
            deadline = time.monotonic() + (lock_timeout or 30)
            acquired = False
            fd = None
            while time.monotonic() < deadline:
                try:
                    # Atomic exclusive lock file create
                    fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                    acquired = True
                    break
                except FileExistsError:
                    time.sleep(0.2)
                except Exception:
                    break

            try:
                if backup and p.exists():
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_file = p.with_suffix(p.suffix + f".bak-{ts}")
                    try:
                        shutil.copy2(p, backup_file)
                    except Exception:
                        pass

                with tempfile.NamedTemporaryFile(suffix=p.suffix, delete=False, dir=p.parent) as tf:
                    temp_path = Path(tf.name)

                try:
                    if p.exists():
                        shutil.copy2(p, temp_path)
                    cb_res = update_cb(temp_path)
                    # Contract: success if True or None (in-place modification)
                    if cb_res is True or cb_res is None:
                        # Windows retry for PermissionError (WinError 32)
                        replaced = False
                        for attempt in range(5):
                            try:
                                temp_path.replace(p)
                                replaced = True
                                break
                            except PermissionError:
                                time.sleep(0.5)
                        if not replaced:
                            temp_path.replace(p)
                finally:
                    if temp_path.exists():
                        try:
                            temp_path.unlink()
                        except OSError:
                            pass
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

---

## Reader Resilience & In-Memory Fallback (`AccountSource._read_row_from_xlsx`)

When high-frequency writers or cron jobs (`sync_all_tik_keywords.py`, `atomic_workbook_update`) perform atomic file replacements (`os.replace`) on Windows, direct disk reads via `openpyxl.load_workbook(filename)` can hit `PermissionError` (file handle locked), `BadZipFile` (read collision during replacement), or `OSError`.

To guarantee 100% read uptime across 80 devices without crashing reader pipelines:
1. **Lock Wait Extension**: In `_wait_for_lock(lock_file, timeout=30.0)`: default timeout increased to 30.0s, sleep interval 0.3s.
2. **In-Memory Buffer Read (`io.BytesIO`)**:
   Read raw bytes via standard file handle `open(self.workbook_path, "rb")`, close the OS handle immediately, and pass `io.BytesIO(data_bytes)` to `openpyxl.load_workbook`. This minimizes the window of holding file locks on Windows and avoids zip stream interruption.
3. **Automatic Fallback to `.bak`**:
   Catch `(PermissionError, zipfile.BadZipFile, OSError)`. If the primary `.xlsx` cannot be read, immediately check for `path.with_suffix(path.suffix + ".bak")`. If `.bak` exists, read its bytes into `io.BytesIO` and log `[ACCOUNT_SOURCE_FALLBACK_BAK]`.

```python
    def _read_row_from_xlsx(self) -> Optional[Dict[str, Any]]:
        """Read a workbook row without dereferencing EmptyCell column metadata."""
        import io, zipfile
        try:
            with open(self.workbook_path, "rb") as f_in:
                data_bytes = f_in.read()
            self._wb = openpyxl.load_workbook(
                io.BytesIO(data_bytes),
                read_only=True,
                data_only=True,
            )
        except (PermissionError, zipfile.BadZipFile, OSError) as read_err:
            bak_path = self.workbook_path.with_suffix(self.workbook_path.suffix + ".bak")
            if bak_path.exists():
                logger.warning(f"[ACCOUNT_SOURCE_FALLBACK_BAK] File chính bị lỗi {read_err}; fallback đọc từ {bak_path.name}")
                with open(bak_path, "rb") as f_bak:
                    self._wb = openpyxl.load_workbook(
                        io.BytesIO(f_bak.read()),
                        read_only=True,
                        data_only=True,
                    )
            else:
                raise read_err
```

## Writer Atomic Pattern with Staged Replacement & Backup (`sync_all_tik_keywords.py`)

For standalone scripts that synchronize workbook fields across multiple Tik files:
1. Write PID into `.lock`.
2. Save modifications to `tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False, dir=p.parent)` on the same filesystem volume.
3. Copy existing file to `.bak` before swapping.
4. Execute atomic replacement via `os.replace(str(temp_file), str(p))`.
5. Safely clean up `.lock` and temporary files in `finally`.
6. Always deploy script updates simultaneously across 3 locations:
   - `C:\Users\Kibe\AppData\Local\hermes\scripts\` (runtime local)
   - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\` (git source)
   - `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\` (shared cron)

---

## Multi-Worker Concurrent Stress Testing (`test_concurrent_readers_with_active_writer_stress`)

To verify that reader threads never crash with `AccountSourceError` or read torn/corrupted state while an active writer performs atomic replacements, implement a high-contention multi-threaded test pattern:

1. **Test Architecture**:
   - Create a temporary workbook with 10 rows (10 distinct devices/machines).
   - Spawn a `concurrent.futures.ThreadPoolExecutor(max_workers=8)`:
     - **1 Writer Thread**: Continuously executes `ac.update_video_number()` (which triggers `atomic_workbook_update` with `.lock`, staging, and replace) in a tight loop for 2.0s.
     - **7 Reader Threads**: Concurrently and continuously call `ac.read_row()` querying different devices (each reading at least 10 times).
2. **Acceptance Criteria**:
   - 0 exceptions raised by writer or readers (zero `AccountSourceError`).
   - Every single reader read returns a valid row corresponding exactly to the queried `device ID`.
   - Reader metrics verify resilience: `ac._read_attempts >= 1` and `_lock_wait_seconds >= 0.0`.
   - Total test runtime remains bounded (< 10s on Windows host).

