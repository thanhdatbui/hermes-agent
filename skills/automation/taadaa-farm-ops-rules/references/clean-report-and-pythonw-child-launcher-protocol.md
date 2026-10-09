# Clean Report Format & pythonw Subprocess Launcher Protocol

## 1. Chuẩn hoá định dạng báo cáo Telegram (User-Mandated)
- **Tối giản & Trực quan (Anti-Accounting Jargon):**
  * Dùng `• Đã hoàn tất: N máy` thay vì chia đôi khó hiểu `• Đã dọn đợt này: N máy` và `• Lũy kế hôm nay: N máy`.
  * Dùng `• Lỗi (N): ...` thay vì `• Fail (N)`.
  * Người vận hành chỉ cần nắm số lượng thực tế đã hoàn thành và danh sách máy gặp lỗi để can thiệp. Tránh tuyệt đối các thuật ngữ thống kê trừu tượng gây hoang mang hoặc hiểu nhầm trạng thái tiến trình.
- **Mẫu báo cáo chuẩn:**
  ```text
  [BÁO CÁO DỌN DẸP CACHE TIKTOK]
  • Đã hoàn tất: 125 máy

  🏢 【FARM KIBE - MÁY 1-80】
  • Đã hoàn tất: 72 máy (01, 02, ...)
  • Lỗi (3): 14, 52, 56
    - Máy 14: Timeout
    - Máy 52: cache row not found on storage screen
    - Máy 56: Timeout

  🏢 【FARM ADMIN - MÁY 201-280】
  • Đã hoàn tất: 53 máy (201, 202, ...)
  • Lỗi (5): 208, 213, 230, 231, 243
  ```

## 2. Xử lý Subprocess dưới daemon pythonw.exe (Windows GUI)
- **Vấn đề console popup:**
  * Khi watchdog/cronjob chạy ngầm dưới `pythonw.exe`, tiến trình cha không sở hữu console subsystem (`sys.executable` trỏ vào `pythonw.exe`).
  * Mọi subprocess con (như `adb.exe shell ...`) được gọi mà không có console kế thừa sẽ làm Windows tự động bật một cửa sổ cmd.exe màu đen chớp tắt trên màn hình người dùng, gây gián đoạn công việc của user.
- **Giải pháp chuẩn hoá:**
  ```python
  _console_python = os.path.join(os.path.dirname(sys.executable), "python.exe")
  CHILD_PYTHON = _console_python if os.path.exists(_console_python) else sys.executable
  ```
  * `CHILD_PYTHON` ưu tiên `python.exe` cùng thư mục cài đặt kết hợp `creationflags=subprocess.CREATE_NO_WINDOW`. Tiến trình con chạy trong console ẩn, đảm bảo mọi lệnh adb kế thừa console này và tuyệt đối không bật popup ra desktop.

## 3. Structured Telemetry & Test Coverage cho Sol Reviewer
- **Observability Rubric Requirement:**
  * Bổ sung log structured telemetry vào `sys.stderr` tại các điểm nhánh: launcher initialization, child fail (`CHILD_FAIL`), timeout (`TIMEOUT`), và ngoại lệ chung (`ERROR`).
  * Định dạng chuẩn: `sys.stderr.write(f"[{c_name.upper()}][TELEMETRY] m={m_num} err=<CHILD_FAIL|TIMEOUT|ERROR> ...\n")`.
  * Không in ra `stdout` để bảo toàn nguyên tắc Silent Watchdog khi không có lỗi hoặc khi chạy bù.
- **Unit Test Coverage bắt buộc:**
  * Kiểm thử resolution của `CHILD_PYTHON`: đảm bảo kiểm tra biến tồn tại và đuôi `.exe`.
  * Bổ sung test assertion mô phỏng đường dẫn launcher dưới `pythonw.exe` và kiểm tra lệnh gọi subprocess truyền đúng `CHILD_PYTHON`.
  * Viết unit test bắt `sys.stderr.write` để chứng minh telemetry được phát ra đúng format khi xảy ra lỗi/timeout.
