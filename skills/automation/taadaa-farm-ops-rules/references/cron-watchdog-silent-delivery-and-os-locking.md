# Kỷ luật Cron Watchdog: Silent Delivery & OS-Level Locking

## 1. Bản chất cơ chế Delivery của Hermes Cron (`no_agent: true`)
- **Semantic:** 
  - `stdout != ""` -> Hermes tự động gửi toàn bộ chuỗi trong `stdout` lên Telegram/chat đích.
  - `stdout == ""` (rỗng) -> Silent: Hermes im lặng hoàn toàn, không gửi bất kỳ tin nhắn nào.
- **Hậu quả nếu vi phạm:** 
  - Bất kỳ lệnh `print()` trung gian nào trong vòng lặp xử lý thiết bị sẽ biến thành tin nhắn spam bắn liên tục lên nhóm chat.
  - Khi gọi các hàm hoặc module con (như `enable_2fa_device`, `atx-agent`, `adb`), các module này thường có sẵn `print()`. Nếu không bọc stream, toàn bộ log debug thô sẽ tràn ra `stdout` và bắn thẳng lên Telegram.

## 2. Quy tắc Bọc Stream (Output Suppression)
Khi thực thi tác vụ bên trong vòng lặp worker / device, BẮT BUỘC dùng context manager để chặn toàn bộ `stdout` và `stderr`:

```python
import io
import contextlib

dev_buf = io.StringIO()
try:
    with contextlib.redirect_stdout(dev_buf), contextlib.redirect_stderr(dev_buf):
        res = execute_device_action(serial, account)
    if not is_success(res):
        # Chỉ ghi chi tiết lỗi vào stderr của cron để điều tra khi cần, KHÔNG in ra stdout
        err_detail = dev_buf.getvalue().strip()
        if err_detail:
            sys.stderr.write(f"[{serial}] Thất bại: {err_detail[-300:]}\n")
except Exception as e:
    sys.stderr.write(f"[{serial}] Exception: {e}\n")
```

## 3. Định dạng Báo cáo Tối giản (Anti-Spam Report Gate)
- **CẤM TUYỆT ĐỐI:** In trực tiếp biểu diễn chuỗi của danh sách raw email / serial (`['M4 (abc@gmail.com)', 'M5 (...)']`) làm tràn màn hình.
- **CHUẨN BÁO CÁO:** Chỉ báo cáo DUY NHẤT 1 LẦN khi toàn bộ ca kết thúc với số liệu tổng hợp cô đọng:
```text
[BÁO CÁO 2FA GMAIL SAU CA SÁNG]
- Thời gian: 10:15 -> 10:15 (0.0 phút)
- Tổng máy xử lý: 79
- Thành công: 79/79 máy
- Thất bại: 0 máy (nếu có lỗi mới liệt kê máy fail: M12, M31)
```

## 4. Singleton Process Lock chuẩn OS Kernel (`msvcrt` trên Windows)
- **CẤM:** Tự chế cơ chế lock file lưu PID và dùng `os.kill(pid, 0)` hoặc `unlink` thủ công. Điều này gây race condition giữa các tick cron kích hoạt đồng thời, và dính lỗi PID reuse trên Windows kernel.
- **CHUẨN:** Dùng advisory file lock của OS kernel:

```python
class ProcessLock:
    """Inter-process lock using OS file locking (msvcrt on Windows, fcntl on POSIX)."""

    def __init__(self, lock_path: str | Path):
        self.lock_path = str(lock_path)
        self._file = None
        self.acquired = False

    def acquire(self) -> bool:
        if self.acquired:
            return False
        handle = None
        try:
            lock_dir = os.path.dirname(self.lock_path)
            if lock_dir:
                os.makedirs(lock_dir, exist_ok=True)
            handle = open(self.lock_path, "a+b")
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._file = handle
            self.acquired = True
            return True
        except (OSError, IOError):
            if handle:
                try:
                    handle.close()
                except Exception:
                    pass
            return False

    def release(self):
        if not self.acquired or not self._file:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        finally:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None
            self.acquired = False
```

## 5. Chuẩn hóa đường dẫn tránh lỗi Escape `\r` trên Windows
Khi code / patch đường dẫn trong các file Python trên Windows, luôn dùng forward slashes (`/`):
- Đúng: `STATE_DIR = "D:/Taadaa/runtime/kibe/cron-state"`
- Tránh: `STATE_DIR = r"D:\Taadaa\runtime\kibe\cron-state"` (chuỗi `\runtime` có chứa `\r` rất dễ bị shell / regex / string parser diễn giải thành byte carriage return gây lỗi `SyntaxError: unterminated string literal`).
