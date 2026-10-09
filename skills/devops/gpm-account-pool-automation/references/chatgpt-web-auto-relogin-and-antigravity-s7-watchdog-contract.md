# ChatGPT-Web Auto-Relogin & Antigravity S7 Watchdog Recovery Contract

## 1. Nguyên Tắc & Yêu Cầu Cốt Lõi Từ User
- **User Directive**: *"Bên chatgpt web bị văng thì tự động login lại chứ mắc gì báo lỗi r khóc"*.
- **Tư duy sai lầm cần diệt trừ**: Watchdog chỉ mở GPM profile lên một cách thụ động, hốt cookie cũ `__Secure-next-auth.session-token` rồi gọi `/api/providers/validate` của OmniRoute. Khi trả về `Validate fail: HTTP Error 400: Bad Request` thì ghi nhận lỗi và dừng lại báo cáo thất bại.
- **Kỷ luật vận hành**: Tài khoản và session là tài sản. Khi session bị invalidated / văng về màn hình đăng nhập, watchdog BẮT BUỘC phải thực hiện luồng **Auto-Relogin** lấy mật khẩu chính chủ để nạp lại cookie mới.

---

## 2. Quy Trình ChatGPT-Web Auto-Relogin Chuẩn Hóa
1. **Dọn dẹp Cookie Cũ**:
   - Khi phát hiện session hết hạn hoặc trang báo `"Your session has expired"` / `"Phiên của bạn đã hết hạn"`:
   - Gọi `context.clear_cookies()` để xóa sạch cookie rác/hết hạn, tránh xung đột vòng lặp redirect của OpenAI.
2. **Kích hoạt Form Đăng Nhập**:
   - Quét và click nút "Log in" / "Đăng nhập" qua các selector:
     `['button[data-testid="login-button"]', 'button:has-text("Log in")', 'button:has-text("Đăng nhập")', 'a:has-text("Log in")', 'a:has-text("Đăng nhập")']`.
3. **Tra cứu Mật khẩu Cột L**:
   - Nguồn mật khẩu ChatGPT chính chủ: Cột L (`PASS CHATGPT` - index 11) trong workbook `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (hoặc `taikhoan_dat_v2_updated.xlsx`).
   - Nếu không có cột L, fallback về mật khẩu Gmail trong `gmail_clean_v2.xlsx` hoặc `master_gmail_manager.xlsx`.
4. **Điền Form & Xử Lý Google SSO**:
   - Điền email vào `input#email-input` / `input[name="email"]` và submit Continue.
   - Nếu form hiện ô nhập password: Điền `PASS CHATGPT` và submit.
   - Nếu OpenAI tự chuyển hướng sang Google SSO: Profile GPM đã đăng nhập sẵn tài khoản Gmail, chọn đúng account row trong Google account chooser hoặc bấm "Tiếp tục" / "Allow".
5. **Trích xuất & Cập nhật Cookie Mới**:
   - Trích xuất cookie đầy đủ (hỗ trợ cả cookie đơn `__Secure-next-auth.session-token` lẫn cookie chunked `.0`, `.1`).
   - Validate cookie với OmniRoute `/api/providers/validate`.
   - Cập nhật database SQLite OmniRoute (`~/.omniroute/storage.sqlite`), reset `last_error=NULL`, đặt `is_active=1`, `test_status='active'`.

---

## 3. Quy Trình Phối Hợp Samsung S7 Khi Antigravity OAuth Dính Challenge
- **Hiện tượng**: Khi re-auth Antigravity OAuth qua GPM browser, Google thường bật màn hình xác minh danh tính.
- **Cơ chế phối hợp S7 có sẵn trong `run_oauth_s7_pipeline.py`**:
  1. **Màn hình chọn phương thức (`challenge/selection`)**:
     - Tự động click tùy chọn `"Mã bảo mật trên điện thoại"` (`div[data-challengetype="8"]`, `li:has-text("mã bảo mật")`).
  2. **Mã bảo mật 10 số offline (`challenge/ootp`)**:
     - Gọi `get_s7_security_code(machine_id, serial, email)`.
     - Script forward cổng ATX-Agent `17000 + machine_id` sang `tcp:7912`.
     - Tự động mở Cài đặt S7 -> Google -> Tài khoản Google -> Bảo mật -> Mã bảo mật.
     - Trích xuất mã 10 số offline (lọc bỏ unicode và khoảng trắng), điền vào ô Pin (`input[name="Pin"]`).
  3. **Google Prompt (`challenge/dp`)**:
     - Bắt số PIN hiển thị trên màn hình PC.
     - Gọi `approve_s7_google_prompt(machine_id, serial, target_pin, target_email=email)`.
     - Tự động kéo thanh thông báo trên S7, chạm thông báo đăng nhập Google và tap nút "Có" / chọn đúng số PIN.

---

## 4. Kỷ Luật Đồng Bộ Script Toàn Farm (3 Nơi & 2-Way Sync)
- **3 Vị trí lưu trữ bắt buộc đồng bộ**:
  1. `D:\Taadaa\Hermes\deploy\hermes-home\scripts\` (Git deploy repo).
  2. `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\` (Kho OneDrive dùng chung Farm).
  3. `%LOCALAPPDATA%\hermes\scripts\` (Runtime thực thi máy Kibe).
- **Cơ chế 2-Way Sync trong `cron_sync_watchdog.py`**:
  - Không chỉ sync từ Runtime sang Deploy, mà khi file trong `DEPLOY_SCRIPTS` có `mtime` mới hơn, script BẮT BUỘC tự động ghi đè sang `KIBE_SCRIPTS` và `ONEDRIVE_SCRIPTS`.
