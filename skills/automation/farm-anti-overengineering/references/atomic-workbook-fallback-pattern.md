# Atomic Workbook Fallback Pattern for Multi-Worker Phone Farm

Được kiểm duyệt và **APPROVED** bởi Claude Sonnet ngày 05/09/2026 sau 3 vòng review phản biện.

## 1. Vấn Đề Thực Tế
Khi nhiều worker / runner chạy đồng thời (16–20 máy) ghi nhận STT video vào chung 1 file Excel (`tik3.xlsx`):
- Nếu runtime thiếu module `automation_core.workbook`, lazy import bị crash (`ModuleNotFoundError`).
- Nếu fallback tự viết thiếu cơ chế khóa (file locking): Dẫn đến race condition, ghi đè mất dữ liệu hoặc làm hỏng file Excel.
- Trên Windows, `Path.replace()` không atomic nếu file đang bị mở tạm bởi process khác (`PermissionError: [WinError 32]`).

## 2. Chuẩn Triển Khai 3 Lớp (Three-Tier Robust Fallback)

```python
# 1. Thử import trực tiếp từ automation-core
try:
    from automation_core.workbook import atomic_workbook_update
except (ImportError, ModuleNotFoundError):
    # 2. Dynamic path detection cho automation-core/src
    import os
    import sys
    from pathlib import Path
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
                    # Tự động dọn stale lock nếu process cũ crash (> 2x timeout)
                    if lock_file.exists():
                        try:
                            if time.time() - lock_file.stat().st_mtime > (lock_timeout or 30) * 2:
                                lock_file.unlink()
                        except OSError:
                            pass

                    # Atomic exclusive lock file create (chống race condition giữa nhiều tiến trình)
                    fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                    acquired = True
                    break
                except FileExistsError:
                    time.sleep(0.2)
                except Exception:
                    break

            # BẮT BUỘC: Lock Enforcement — Nếu không lấy được lock thì raise TimeoutError ngay
            if not acquired:
                raise TimeoutError(f"Could not acquire lock on {lock_file} within {lock_timeout}s")

            try:
                # Tạo backup file trước khi chỉnh sửa
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
                    
                    # Contract: chấp nhận thành công nếu callback trả về True hoặc None (in-place)
                    if cb_res is True or cb_res is None:
                        # Windows PermissionError retry loop (5 lần x 0.5s backoff)
                        replaced = False
                        for attempt in range(5):
                            try:
                                temp_path.replace(p)
                                replaced = True
                                break
                            except PermissionError:
                                time.sleep(0.5)
                        if not replaced:
                            temp_path.replace(p)  # Lần cuối để exception propagate nếu file thực sự bị khóa chết
                finally:
                    if temp_path.exists():
                        try:
                            temp_path.unlink()
                        except OSError:
                            pass
            finally:
                # Luôn giải phóng lock sạch sẽ
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

## 3. Checklist An Toàn Khi Chỉnh Sửa Logic Workbook
1. **Never bypass lock silently:** Nếu không acquire được lock, cấm tiếp tục ghi đè file. Bắt buộc `raise TimeoutError`.
2. **Handle Windows WinError 32:** Luôn có retry loop bắt `PermissionError` khi gọi `replace()`.
3. **Stale Lock Recovery:** Tránh deadlock vĩnh viễn khi tiến trình con bị task manager kill hoặc OOM bằng cơ chế kiểm tra `mtime > 2 * timeout`.
4. **Close fd before unlink:** Trên Windows, file đang mở handle không thể unlink được. Phải `os.close(fd)` trước `lock_file.unlink()`.
