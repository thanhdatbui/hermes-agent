# ChatGPT Registration & Google OAuth Flow via GPMLogin CDP

## 1. Bối cảnh & Mục đích
Tự động đăng nhập / khởi tạo tài khoản ChatGPT qua Google Account (`Continue with Google`) trên các profile GPMLogin đã có sẵn phiên đăng nhập Gmail.

---

## 2. Các cạm bẫy thực chiến & Cách khắc phục (Pitfalls & Solutions)

### Pitfall 1: Bẫy "Guest Landing Page" của ChatGPT (False Positive Logged-in)
- **Triệu chứng**: Khi chưa đăng nhập, ChatGPT vẫn hiển thị ô nhập prompt textarea (`Hỏi ChatGPT` / `Ask ChatGPT`) kèm banner cookie và các nút "Đăng nhập", "Đăng ký".
- **Hậu quả**: Nếu chỉ kiểm tra `chatgpt.com in page.url` hoặc sự xuất hiện của `textarea`, script sẽ bị đánh lừa là "đã đăng nhập thành công", thoát sớm và chụp ảnh màn hình chưa đăng nhập.
- **Giải pháp chuẩn**:
  - Bắt buộc kiểm tra KHÔNG CÒN nút đăng nhập:
    `button:has-text("Đăng nhập")`, `button:has-text("Log in")`, `button:has-text("Sign up")`, `[data-testid="login-button"]`.
  - Phải kiểm tra sự xuất hiện của nút profile / user menu:
    `button[data-testid="profile-button"]`, `[aria-label*="User menu"]`, `[aria-label*="Menu người dùng"]`.

### Pitfall 2: Bẫy Container Selector trên Google Account Chooser
- **Triệu chứng**: Khi popup Google Sign-in hiện danh sách tài khoản, nếu dùng selector rộng `div:has-text("email@gmail.com")`, Playwright sẽ click trúng thẻ container ngoài cùng (`div#view_container`) thay vì hàng tài khoản có thể click được. Sự kiện click bị nuốt chửng, không có điều hướng.
- **Giải pháp chuẩn**:
  - Dùng đúng selector chuyên biệt của Google Account Chooser:
    ```python
    google_page.locator(f'div[data-identifier="{email}"], [data-email="{email}"], li:has-text("{email}") div[role="link"]').first.click()
    # Hoặc fallback:
    google_page.get_by_text(email, exact=False).first.click()
    ```

### Pitfall 3: Xung đột PYTHONPATH Hermes Agent với Playwright môi trường ngoài
- **Triệu chứng**: Khi script con chạy bằng Python `automation` (3.12) nhưng thừa hưởng `PYTHONPATH` trỏ vào venv Hermes (3.11), Playwright ném lỗi binary C-extension `ModuleNotFoundError: No module named 'greenlet._greenlet'`.
- **Giải pháp chuẩn**:
  - Luôn khởi chạy script bằng `env -u PYTHONPATH` hoặc gọt sạch `sys.path` đầu file:
    ```python
    import sys
    sys.path = [p for p in sys.path if "hermes-agent" not in p]
    ```

### Pitfall 4: GPM Browser Core 142 không hỗ trợ `--remote-debugging-pipe`
- **Triệu chứng**: Gọi `launch_persistent_context` trực tiếp trên binary GPM Chrome văng lỗi `exitCode=21` vì Chrome Core 142 của GPM yêu cầu cổng debug TCP socket.
- **Giải pháp chuẩn**:
  - Khởi động profile qua Local API v3: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
  - Lấy `remote_debugging_address` từ response và kết nối qua `p.chromium.connect_over_cdp(f"http://{remote_debugging_address}")`.

---

## 3. Quy trình chuẩn Onboarding ChatGPT cho tài khoản mới

1. **Cookie Banner**: Click nút chấp nhận `Chấp nhận tất cả` / `Accept all` ngay khi tải trang `https://chatgpt.com/auth/login`.
2. **Kích hoạt OAuth**: Click `Continue with Google` (`button[data-provider="google"]` hoặc text `Tiếp tục với Google`).
3. **Google Sign-in / Consent**:
   - Chọn đúng tài khoản Gmail trên danh sách account chooser.
   - Nếu hiện trang cấp quyền OAuth (`#submit_approve_access`): click "Tiếp tục" / "Cho phép".
4. **Màn hình Onboarding OpenAI ("Tell us about you")**:
   - Điền Full Name (nếu input trống).
   - Điền Birthday hợp lệ (> 18 tuổi, vd: `15/08/1998` hoặc định dạng YYYY-MM-DD tương ứng).
   - Click `Agree` / `Continue`.
5. **Xử lý Checkpoint Số điện thoại (Phone Verification)**:
   - Nếu xuất hiện yêu cầu số điện thoại (`input[type="tel"]` hoặc `Verify your phone number`):
   - Chụp ảnh màn hình lưu `chatgpt_{email}_phone_req.png`, ghi nhận trạng thái `PHONE_VERIFICATION_REQUIRED` và chuyển tiếp acc khác, không để luồng bị treo.
6. **Đóng Profile**: Luôn đặt lệnh gọi `stop_profile` qua GPM API trong khối `finally` để giải phóng tiến trình Chrome.
