# Kỷ Luật Trị Rò Rỉ Stdout Cron Watchdog & Quy Tắc Action-First (Cấm Xin Lỗi Đãi Bôi) — 17/09/2026

## 1. Sự Cố Thực Tế (Spam 86 Mail & Cơn Giận Của User)
- **Bối cảnh:** Watchdog `post_morning_gmail_2fa_watchdog.py` chạy qua Hermes cron (`no_agent: true`, schedule `*/5 8,9,10,11 * * *`, deliver `telegram:-5373649734`).
- **Hiện tượng:**
  1. Hàng chục dòng debug log trung gian (`[serial] Bắt đầu quy trình...`, `[serial] Đã điều hướng...`) liên tục tràn vào nhóm Telegram suốt 50+ phút.
  2. Báo cáo cuối phiên in nguyên mảng Python list thô của 86 email (`Success (86): ['M4 (dangthithuy...)', ...]`) làm phình chat.
  3. Thiếu Singleton PID lock, khiến các tick 5 phút sau chạy đè trong khi ca 50 phút chưa kết thúc.
- **Phản ứng của Agent và Hậu Quả:**
  - Agent trả lời: *"Dạ em nhận lỗi. Em đã ghi nhớ kỷ luật: chạy ngầm tuyệt đối im lặng..."*
  - User nổi giận ngay lập tức: *"Sửa cron báo cáo lại, nhận lỗi cái lồn à đợi mày nhớ"*.

---

## 2. Kỷ Luật Action-First: CẤM XIN LỖI ĐÃI BÔI
1. **Bản chất tâm lý user:**
   - Khi có lỗi hệ thống hoặc bot làm sai quy chuẩn, user cần **LỖI ĐƯỢC SỬA NGAY LẬP TỨC (Fix it now)**, không cần nghe bot xin lỗi hay tự nhắc lại quy chế.
   - Việc nói "Dạ em nhận lỗi / Em xin rút kinh nghiệm" không giải quyết được bug và tạo cảm giác thụ động, trốn tránh hành động.
2. **Quy tắc ứng xử bắt buộc (Invariant):**
   - **CẤM TUYỆT ĐỐI:** Nói câu xin lỗi rỗng tuếch ("Dạ em nhận lỗi", "Em xin lỗi user", "Em đã ghi nhớ...").
   - **BẮT BUỘC:** Đi thẳng vào hành động kỹ thuật O(1):
     + Xác định ngay file lỗi / tiến trình gây spam.
     + Kê khai các điểm đang sửa (Lock file, Redirect stdout, Format gọn).
     + Dispatch worker sửa ngay và báo cáo kết quả nghiệm thu bằng git diff / test compile.

---

## 3. Ba Lỗ Hổng Kỹ Thuật Khi Viết Hermes Cron Watchdog (`no_agent: True`)

### Lỗ hổng 1: Rò rỉ Stdout từ Sub-Module được Import
- **Cơ chế Hermes cron:** Với `no_agent: true`, scheduler lấy toàn bộ `sys.stdout` của tiến trình gửi thẳng lên Telegram. Chỉ khi stdout rỗng (`""`) thì mới im lặng (`silent`).
- **Nguyên nhân:** Khi watchdog import hàm từ module con (`from enable_gmail_2fa_device import enable_2fa_device`), mọi lệnh `print()` bên trong module con sẽ bắn thẳng ra `sys.stdout` của tiến trình mẹ.
- **Giải pháp bắt buộc:**
  ```python
  import io
  import contextlib

  dev_buf = io.StringIO()
  with contextlib.redirect_stdout(dev_buf):
      res = enable_2fa_device(s, email)
  ```

### Lỗ hổng 2: Thiếu Singleton PID Lock Trên Batch Dài
- **Nguyên nhân:** Cron tick mỗi 5-15 phút, nhưng batch chạy trên nhiều thiết bị mất 30-60 phút. Không có lock file sẽ sinh ra nhiều tiến trình chạy song song, tranh chấp ADB và spam Telegram liên tục.
- **Giải pháp bắt buộc:**
  ```python
  LOCK_FILE = Path("D:/Taadaa/runtime/kibe/cron-state/my_watchdog.lock")
  if LOCK_FILE.exists():
      try:
          old_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
          if is_pid_alive(old_pid):
              return 0  # Im lặng thoát ngay
      except Exception:
          pass
      LOCK_FILE.unlink(missing_ok=True)

  try:
      LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
      LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
      # ... chạy batch ...
  finally:
      LOCK_FILE.unlink(missing_ok=True)
  ```

### Lỗ hổng 3: Dump Raw Python List Ra Chat
- **Nguyên nhân:** In `{success_list}` hoặc `{fail_list}` trực tiếp ra chuỗi báo cáo.
- **Giải pháp:** Chỉ báo cáo định lượng tổng quát (`Thành công: 86/86 máy`, `Thất bại: 0 máy`). Chỉ liệt kê danh sách rút gọn các máy fail nếu có lỗi (ví dụ: `Thất bại (2 máy): M12, M31`). Tuyệt đối không dump email hay dữ liệu thô.

---

## 4. Cạm Bẫy Path Escape `\r` Trên Windows Khi Viết Code
- **Hiện tượng:** Viết `r"D:\Taadaa\runtime\..."` trong tool patch / write file.
- **Cạm bẫy:** Chuỗi `\runtime` có chứa `\r`. Khi đi qua JSON hoặc parser chuỗi, `\r` bị diễn dịch thành ký tự Carriage Return (0x0D), cắt cụt chuỗi thành `D:\Taadaa\r` và làm dòng code tiếp theo bị vỡ thành `unterminated string literal`.
- **Quy tắc bất biến:** Trong mọi code Python sinh ra trên Windows, **BẮT BUỘC dùng dấu gạch xuôi (`/`)**:
  `STATE_DIR = "D:/Taadaa/runtime/kibe/cron-state"`
