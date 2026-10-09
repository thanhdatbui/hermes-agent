# Resilient 3-Tier Fallback cho `atomic_workbook_update` (Case 85)

Áp dụng cho mọi Consumer Repos (`Tiktok-video`, `tiktok-follow`, `Tiktok_Reg`, `tiktok-luot nuoi acc`...) khi tương tác với file Excel Workbook (`tik1.xlsx`, `tik2.xlsx`, `tik3.xlsx`, `taikhoan_run_safe.xlsx`).

---

## 1. Bối cảnh & Hiện tượng lỗi (Sự cố Máy 69)
- **Triệu chứng:** Worker upload hoặc feed hoàn thành 100% nhiệm vụ chính trên profile TikTok, nhưng khi chuyển sang state `UPDATE_WORKBOOK` thì crash:
  ```text
  [WORKBOOK_UPDATE_FAILED] UPDATE_WORKBOOK: Workbook update failed: No module named 'automation_core.workbook'
  ```
- **Nguyên nhân gốc rễ (Anti-Pattern):**
  1. Lazy import cứng `from automation_core.workbook import atomic_workbook_update` trực tiếp bên trong method cập nhật mà không có khối `try...except` dự phòng. Khi runner khởi chạy trong sub-environment/toolchain thiếu module này trên `sys.path`, tiến trình văng `ModuleNotFoundError`.
  2. Fallback inline nếu viết sơ sài (thiếu file lock concurrency, bỏ qua `lock_timeout`, không phá stale lock khi crash cũ, hoặc không bọc retry bắt `PermissionError` trên Windows) sẽ dẫn tới corrupt file Excel hoặc ghi đè mất dữ liệu khi nhiều runner chạy song song.

---

## 2. Chuẩn Triển Khai Fallback 3 Tầng (Canonical Pattern)

Đặt khối code sau tại vị trí import `atomic_workbook_update`:

```python
        # 1. Tầng 1: Thử import trực tiếp từ automation_core.workbook
        try:
            from automation_core.workbook import atomic_workbook_update
        except (ImportError, ModuleNotFoundError):
            # 2. Tầng 2: Dynamic path detection cho automation-core/src
            import os
            import sys
            env_ac = os.environ.get("AUTOMATION_CORE_SRC")
            candidate_paths = [
                Path(env_ac) if env_ac else None,
                Path(__file__).resolve().parents[3] / "automation-core" / "src",
                Path("D:/Taadaa/automation-core/src"),
            ]
            for cand in candidate_paths:
                if cand and cand.is_dir():
                    if str(cand) not in sys.path:
                        sys.path.insert(0, str(cand))
                    try:
                        from automation_core.workbook import atomic_workbook_update
                        break  # Dừng ngay khi import thành công để tránh pollute sys.path
                    except (ImportError, ModuleNotFoundError):
                        continue
            try:
                from automation_core.workbook import atomic_workbook_update
            except (ImportError, ModuleNotFoundError):
                # 3. Tầng 3: Fallback inline robust (chống race condition và Windows PermissionError)
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
                            # Break stale lock nếu tuổi thọ > 2x timeout (tiến trình cũ bị crash)
                            if lock_file.exists():
                                try:
                                    if time.time() - lock_file.stat().st_mtime > (lock_timeout or 30) * 2:
                                        lock_file.unlink()
                                except OSError:
                                    pass
                            # Atomic exclusive lock file create (Windows NTFS & POSIX)
                            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                            acquired = True
                            break
                        except FileExistsError:
                            time.sleep(0.05)
                        except Exception:
                            break

                    # BẮT BUỘC: Lock enforcement (raise TimeoutError nếu không lấy được lock)
                    if not acquired:
                        raise TimeoutError(f"Could not acquire lock on {lock_file} within {lock_timeout}s")

                    try:
                        # Tạo backup an toàn
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
                            # Contract: Thành công nếu trả về True hoặc None (modify in-place)
                            if cb_res is True or cb_res is None:
                                # Windows retry với exponential backoff bắt PermissionError (WinError 32)
                                replaced = False
                                for attempt in range(5):
                                    try:
                                        temp_path.replace(p)
                                        replaced = True
                                        break
                                    except PermissionError:
                                        time.sleep(min(0.2 * (2 ** attempt), 2.0))
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

## 3. Các Điểm Bắt Buộc Tuân Thủ (Invariants)
1. **Monotonic Check Nằm Trong Lock:** Kiểm tra tiến trình STT video không được thụt lùi (`effective_video_number = max(current_video_number, requested_video_number)`) BẮT BUỘC phải nằm bên trong `update_cb` để được bao bọc bởi lock.
2. **Lock Enforcement:** Nếu hết `lock_timeout` mà chưa lấy được lock, BẮT BUỘC phải `raise TimeoutError`, tuyệt đối không được tiếp tục ghi file.
3. **Stale Lock Recovery:** Tự động giải phóng lock file cũ mồ côi nếu `st_mtime > 2 * lock_timeout`.
4. **Exponential Backoff:** Bắt `PermissionError` trên Windows với backoff `min(0.2 * 2**attempt, 2.0)` để chờ file handle đóng xong.

---

## 4. Đối Xứng Phía Đọc: Lock-Wait & Retry Backoff cho Readers (`AccountSource.read_row`)

### Bối cảnh & Triệu chứng
Khi 30–40 worker hoàn tất upload cùng lúc (như đợt hoàn tất batch), nhiều tiến trình gọi `atomic_workbook_update` để cập nhật số video đã đăng. Cùng lúc đó, các worker khác đến nhịp đọc workbook (`AccountSource.read_row()`).
Nếu phía đọc (`read_row`) mở file bằng `openpyxl.load_workbook(..., read_only=True)` đúng khoảnh khắc file gốc đang bị `temp_path.replace(p)` hoặc OneDrive đồng bộ:
- Windows trả về dữ liệu rỗng/chưa hoàn chỉnh, thiếu header hoặc thiếu cell.
- Hàm `validate_row()` văng lỗi:
  ```text
  [READ_WORKBOOK_ERROR] Missing required fields: ID TikTok
  ```
- Worker lập tức kết luận job fail và kích hoạt ATX-restart vô ích, làm hỏng phiên của nhiều máy.

### Chuẩn Triển Khai Cho Phía Đọc (`read_row`)
Phía đọc BẮT BUỘC phải đối xứng với phía ghi:
1. **Chờ Lock Nhả:** Kiểm tra file `.lock` của workbook. Nếu tồn tại, chờ tối đa 10s (poll mỗi 0.2s; tự động unlink stale lock > 60s).
2. **Retry Loop với Backoff:** Bọc `_read_row_from_xlsx()` trong vòng lặp thử lại tối đa 5 lần với backoff `0.5s * attempt` (0.5s $\to$ 1.0s $\to$ 1.5s $\to$ 2.0s $\to$ 2.5s).
3. **Đóng Handle Triệt Để:** Trong khối `except Exception`, luôn gọi `_wb.close()` và gán `_wb = None` để không giữ open handle trên Windows.

```python
        # 1. Chờ tiến trình khác ghi xong qua file .lock
        lock_file = self.workbook_path.with_suffix(self.workbook_path.suffix + ".lock")
        if lock_file.exists():
            lock_deadline = time.monotonic() + 10.0
            while lock_file.exists() and time.monotonic() < lock_deadline:
                try:
                    if time.time() - lock_file.stat().st_mtime > 60:
                        lock_file.unlink()
                        break
                except OSError:
                    pass
                time.sleep(0.2)

        # 2. Thử lại tối đa 5 lần với exponential/linear backoff
        max_attempts = 5
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                row = self._read_row_from_xlsx()
                if self._wb is not None:
                    self._wb.close()
                    self._wb = None
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
```

