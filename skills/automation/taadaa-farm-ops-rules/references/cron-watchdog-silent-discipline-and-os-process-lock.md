# Kỷ Luật Watchdog Cron Im Lặng Tuyệt Đối & Khóa OS ProcessLock

## 1. Bản Chất Delivery Của Hermes Cron (`no_agent: true`)
- **Cơ chế gửi tin nhắn:**
  - Đối với cron job cấu hình `no_agent: true`, hệ thống bắt toàn bộ `sys.stdout` của script để làm nội dung tin nhắn Telegram.
  - **`stdout` có nội dung bất kỳ:** Hermes lập tức bắn nguyên văn nội dung đó vào chat/group tương ứng (`deliver: origin` hoặc `deliver: telegram:<chat_id>`).
  - **`stdout` rỗng (`""`):** Cron im lặng tuyệt đối (Watchdog Silent Pattern). Không có tin nhắn nào được gửi đi.
  - **Script crash / non-zero exit code:** Hermes gửi alert cảnh báo lỗi tiến trình.

## 2. Kỷ Luật "Im Lặng Tuyệt Đối Khi Đang Chạy" (Silent Execution)
- **Nguyên nhân gây spam rác:**
  - Khi một watchdog gọi hàm nghiệp vụ trực tiếp qua import (ví dụ: `enable_2fa_device`, `register_chatgpt_on_device`), các lệnh `print()` nội bộ của module đó sẽ xuất thẳng ra `sys.stdout`.
  - Nếu tiến trình chạy qua 40-80 máy kéo dài 30-60 phút, toàn bộ 10-20KB log trung gian debug sẽ bị tống thẳng vào Telegram của User.
- **Quy tắc bắt buộc (Stdout/Stderr Suppression):**
  - MỌI lệnh gọi module con phải được bọc kín stream để không lọt 1 byte ra `stdout`:
    ```python
    import io
    import contextlib

    dev_buf = io.StringIO()
    with contextlib.redirect_stdout(dev_buf), contextlib.redirect_stderr(dev_buf):
        res = worker_function(device_serial, account)
    ```
  - Nếu thất bại và cần lưu log điều tra, CHỈ trích xuất vài trăm ký tự cuối từ `dev_buf` và ghi ra `sys.stderr` qua `log(...)` (không ảnh hưởng tới `stdout` của cron):
    ```python
    if not is_success:
        err_detail = dev_buf.getvalue().strip()
        if err_detail:
            sys.stderr.write(f"[FAIL] {machine_id}: {err_detail[-300:]}\n")
    ```

## 3. Kỷ Luật Định Dạng Báo Cáo Nghiệm Thu (Anti-Data Dump)
- **CẤM TUYỆT ĐỐI:**
  - CẤM in mảng thô (Python raw `list`) chứa hàng chục email, token hoặc đường dẫn dài ngoằng vào báo cáo (`Success (86): ['M4 (email1)', 'M5 (email2)'...]`).
  - CẤM spam thông báo lẻ tẻ từng máy hoàn thành trong các vòng lặp định kỳ 5 phút.
- **QUY CHUẨN BÁO CÁO CÔ ĐỌNG (DUY NHẤT 1 LẦN KHI XONG E2E):**
  - Chỉ xuất đúng 1 block báo cáo từ 4-5 dòng có cấu trúc rõ ràng:
    ```text
    [BÁO CÁO 2FA GMAIL SAU CA SÁNG]
    - Thời gian: 08:35 -> 09:42 (67.0 phút)
    - Tổng máy xử lý: 79
    - Thành công: 79/79 máy
    - Thất bại: 0 máy
    ```
  - Nếu có máy lỗi, chỉ liệt kê định danh máy vắn tắt (ví dụ: `- Thất bại (2 máy): M12, M31`), không dump email.

## 4. Cơ Chế Khóa Tiến Trình Chuẩn Kernel (OS-Level ProcessLock)
- **Cạm bẫy của việc tự viết Lock file kiểm tra PID:**
  1. Dùng `os.kill(pid, 0)` không hoạt động chuẩn xác trên Windows (Unix-style signal).
  2. Rủi ro PID reuse: Trên Windows, sau khi process cũ chết, OS có thể cấp phát lại PID đó cho một app khác, khiến lock tưởng process vẫn sống và vĩnh viễn không chạy lại.
  3. Race condition khi xử lý stale lock: Tiến trình thấy lock cũ chết, gọi `unlink()` rồi mới `open()` thì bị tiến trình khác nhảy vào giữa, làm mất lock hoặc chạy song song.
- **Giải pháp chuẩn hóa toàn Farm (ProcessLock):**
  - Sử dụng OS advisory locking qua `msvcrt.locking` trên Windows và `fcntl.flock` trên POSIX.
  - Khi tiến trình thoát bình thường hoặc crash đột ngột (kể cả BSOD / kill task), OS Kernel tự động đóng file descriptor và nhả lock tức thì.
  - **Mã nguồn chuẩn sử dụng trong các watchdog farm:**
    ```python
    import os
    from pathlib import Path

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

## 5. Cạm Bẫy Ký Tự Escape Đường Dẫn Windows (`\r`)
- Trong các script Python chạy trên môi trường Windows / MSYS2, tránh dùng raw string có `\r` như `r"D:\Taadaa\runtime\..."`.
- Một số công cụ subshell / patch regex có thể diễn giải `\r` thành byte carriage return (`\x0d`), dẫn đến ngắt dòng file và gây lỗi `SyntaxError: unterminated string literal`.
- **Quy tắc:** Luôn dùng dấu xuyệt xuôi (forward slashes) cho toàn bộ đường dẫn trong Python: `"D:/Taadaa/runtime/kibe/cron-state"`.
