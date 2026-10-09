# Kỷ Luật Watchdog Cron: Chạy Ngầm Im Lặng Tuyệt Đối & Định Dạng Báo Cáo Chuẩn

## 1. Bản Chất Delivery Của Cron (no_agent = True)
- **Cơ chế:** Bất kỳ nội dung nào được in ra `sys.stdout` trong quá trình cron job thực thi đều được Hermes Gateway chuyển tiếp thẳng về kênh đích (Telegram Group / Chat).
- **Hệ quả chết người:** Nếu trong script gọi hàm của module con (hoặc import module) mà bên trong module đó có các lệnh `print(...)` tiến độ (ví dụ: `print("[serial] Bắt đầu...", "Đã điều hướng...")`), toàn bộ log trung gian sẽ bị đẩy lên Telegram theo từng đợt, làm spam nhóm chat của user.
- **Nguyên tắc bất di bất dịch:** Trong suốt thời gian chạy ngầm (dù kéo dài 30–60 phút), `sys.stdout` PHẢI HOÀN TOÀN TRỐNG RỖNG (`stdout == ""`).

## 2. Kỹ Thuật Redirect / Chặn Rò Rỉ Log Trung Gian
Khi gọi bất kỳ hàm tự động hóa thiết bị hoặc script con nào có khả năng `print` ra stdout:
```python
import io
import contextlib

# Chặn toàn bộ print() bên trong module con tràn ra sys.stdout của cron
dev_buf = io.StringIO()
with contextlib.redirect_stdout(dev_buf):
    res = enable_2fa_device(serial, email)

# Nếu cần ghi log phục vụ debug nội bộ trên máy, CHỈ ghi vào sys.stderr hoặc file log:
# sys.stderr.write(dev_buf.getvalue())
```

## 3. Singleton Process Lock (Chống Re-entrancy Khi Cron Lặp Tần Suất Cao)
- **Vấn đề:** Cron thường đặt lịch kiểm tra mỗi 5 phút (`*/5`), nhưng một batch xử lý nhiều máy có thể kéo dài 40–60 phút.
- **Hậu quả nếu thiếu lock:** Mỗi 5 phút cron lại kích hoạt một tiến trình mới, chạy song song, tranh chấp thiết bị và liên tục bắn báo cáo đè lên nhau.
- **Giải pháp chuẩn:**
  ```python
  import os
  import psutil
  from pathlib import Path

  LOCK_FILE = Path(r"D:\Taadaa\runtime\kibe\cron-state\my_watchdog.lock")

  def check_and_acquire_lock() -> bool:
      if LOCK_FILE.exists():
          try:
              pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
              if psutil.pid_exists(pid):
                  return False  # Đang có tiến trình khác chạy -> Im lặng thoát
          except Exception:
              pass
          LOCK_FILE.unlink(missing_ok=True)

      LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
      LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
      return True

  def release_lock():
      LOCK_FILE.unlink(missing_ok=True)
  ```
- Trong `main()`: Bọc toàn bộ luồng chạy trong `try...finally: release_lock()`.

## 4. Chuẩn Định Dạng Báo Cáo Nghiệm Thu Cuối Cùng
- **Chỉ báo cáo ĐÚNG 1 LẦN duy nhất** khi toàn bộ batch hoàn tất e2e.
- **CẤM TUYỆT ĐỐI:**
  - Dump raw Python data structures (`list`, `dict`).
  - In danh sách hàng chục/hàng trăm địa chỉ email, serial thiết bị thô gây dài ngoằng tin nhắn.
- **Định dạng chuẩn cô đọng (3–5 dòng):**
  ```text
  [BÁO CÁO 2FA GMAIL SAU CA SÁNG]
  - Thời gian: 08:50 -> 09:42 (52 phút)
  - Tổng máy xử lý: 86
  - Thành công: 86/86 máy
  - Thất bại: 0 máy
  ```
- **Nếu có máy thất bại:** Chỉ liệt kê ngắn gọn số hiệu máy lỗi (ví dụ: `Thất bại (2 máy): M12, M31`), tuyệt đối không kèm email/token/credentials.
- **Ghi nhận State Idempotency:** Ngay sau khi print báo cáo tổng kết, bắt buộc cập nhật state file (`last_success_date = today` hoặc `reported = True`) để các tick cron tiếp theo trong ngày tự động bỏ qua.
