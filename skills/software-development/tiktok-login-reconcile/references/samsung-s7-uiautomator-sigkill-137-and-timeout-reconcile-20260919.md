# Samsung S7 UiAutomator SIGKILL 137 & Subprocess Timeout Fix (2026-09-19)

## 1. Bản chất sự cố
- Trên dòng máy Samsung Galaxy S7 (Android 7.0 / 8.0), daemon `uiautomator` hệ thống thường xuyên bị crash hoặc bị kernel kết liễu với exit code `137` (SIGKILL do OOM hoặc deadlock tại `futex_wait_queue_me`).
- Khi daemon bị lỗi, các script tự động gọi `adb shell uiautomator dump` sẽ:
  1. Trả về mã lỗi 137 ngay lập tức và sinh ra file XML rỗng hoặc XML cũ bị stale.
  2. Hoặc tệ hơn, tiến trình ADB bị nghẽn (hang vô hạn) nếu `subprocess.run()` không thiết lập tham số `timeout`.
- Khi worker chạy các script như `do_logout_account.py` mà thiếu `timeout`, toàn bộ tiến trình subagent bị block cứng cho tới khi chạm ngưỡng timeout tối đa (600s).

## 2. Quy tắc an toàn bắt buộc (Safety Invariants)
1. **Mọi lệnh gọi ADB subprocess BẮT BUỘC có timeout**:
   ```python
   # CẤM:
   subprocess.run([ADB, "-s", serial] + args, capture_output=True)

   # BẮT BUỘC:
   subprocess.run([ADB, "-s", serial] + args, capture_output=True, timeout=15)
   ```
2. **Không phụ thuộc duy nhất vào `uiautomator dump`**:
   - Khi `uiautomator dump` trả về exit code 137, script BẮT BUỘC fail-soft sang cơ chế **Screencap + Windows Native OCR (`do_ocr.ps1`)** hoặc **Tọa độ chuẩn hóa (Normalized Coordinates)**.
3. **Kỷ luật nghiệm thu Đăng xuất nick ký sinh (2-Layer Verification)**:
   - CẤM bấm nút Đăng xuất rồi tự động kết luận thành công và ghi state "DONE".
   - BẮT BUỘC mở lại Profile -> mở Switcher -> chụp screencap và OCR/inspect XML:
     - Xác nhận nick ký sinh **ĐÃ BIẾN MẤT** khỏi Switcher.
     - Xác nhận nút **"Thêm tài khoản"** (Add account) đã xuất hiện lại hoặc số lượng tài khoản giảm về đúng 7.
