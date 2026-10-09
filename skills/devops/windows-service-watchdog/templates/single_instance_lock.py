"""
Cross-platform Single-Instance Lock for Windows and Unix.
Prevents concurrent execution of cron jobs, watchdogs, and background healers.
Uses kernel-level advisory locks (msvcrt on Windows, fcntl on Unix).
Automatically released by the OS kernel when the process terminates or crashes.
"""

import os
import sys
import datetime
from pathlib import Path
from typing import Optional, Any

class SingleInstanceLock:
    """
    Guarantees that only one process can execute the protected critical section.
    Unlike naive file existence checks, kernel-level byte locks are automatically
    released by the OS even if the process crashes, is killed, or exits abruptly.
    """
    def __init__(self, lock_file_path: Path):
        self.lock_file_path = Path(lock_file_path)
        self._fp: Optional[Any] = None
        self.is_locked: bool = False

    def acquire(self) -> bool:
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if not self.lock_file_path.exists():
                self.lock_file_path.touch()
            self._fp = open(self.lock_file_path, "r+b")
            self._fp.seek(0)
            if os.name == "nt":
                import msvcrt
                # LK_NBLCK: Non-blocking lock 1 byte from current position (offset 0)
                msvcrt.locking(self._fp.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Record PID and timestamp for triage
            self._fp.seek(0)
            self._fp.truncate()
            self._fp.write(f"pid={os.getpid()}\ntime={datetime.datetime.now().isoformat()}\n".encode("utf-8"))
            self._fp.flush()
            self.is_locked = True
            return True
        except (IOError, OSError):
            if self._fp:
                try:
                    self._fp.close()
                except Exception:
                    pass
                self._fp = None
            self.is_locked = False
            return False

    def release(self):
        if self._fp and self.is_locked:
            try:
                if os.name == "nt":
                    import msvcrt
                    self._fp.seek(0)
                    msvcrt.locking(self._fp.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fp.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self._fp.close()
            except Exception:
                pass
            self._fp = None
            self.is_locked = False

    def __enter__(self):
        if not self.acquire():
            raise BlockingIOError(f"Another instance is already running (lock: {self.lock_file_path})")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
