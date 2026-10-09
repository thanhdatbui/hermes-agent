# Chẩn đoán trạng thái tài khoản Gmail (Google Login Probe Pattern)

## Mục đích
Khi một lô tài khoản bị lỗi hoặc nghi ngờ die/checkpoint, dùng pattern probe nhanh không lưu cache để xác định chính xác Google đang phản hồi gì cho từng tài khoản (ACCOUNT_NOT_FOUND, VERIFY_REQUIRED, PHONE_CHALLENGE, WRONG_PASSWORD hay ACCOUNT_DISABLED).

## Quy trình Probe nhanh & Tiết kiệm tài nguyên
1. **Tạo Profile GPM tạm thời:**
   - Tạo profile với `raw_proxy: ""` (direct IP) hoặc proxy tương ứng nếu cần.
   - Không gắn profile vào group vĩnh viễn, đặt tên tiền tố `probe_<email_prefix>`.

2. **Kết nối Playwright CDP:**
   - Start profile qua GPM API v3 (`GET /api/v3/profiles/start/{id}`).
   - Connect Playwright qua `browser = p.chromium.connect_over_cdp(f"http://{remote_debugging_address}")`.

3. **Điều hướng ServiceLogin:**
   - Goto `https://accounts.google.com/ServiceLogin` với `wait_until="domcontentloaded"`.
   - Điền email vào input (`input[type="email"], input#identifierId, input[name="identifier"]`).
   - Click Next (`#identifierNext button`).
   - Đợi 2.5 - 3 giây để Google xử lý validation email.

4. **Phân loại trạng thái chính xác (Response Gate):**
   - **`ACCOUNT_NOT_FOUND`**:
     - Dấu hiệu: DOM chứa `"không tìm thấy tài khoản google"`, `"couldn't find your google account"`, `"couldn't find your account"`.
     - Ý nghĩa: Tài khoản đã bị xoá vĩnh viễn khỏi Google (không thể khôi phục).
   - **`VERIFY_REQUIRED / PHONE_CHALLENGE`**:
     - Dấu hiệu: Sau khi submit email, không xuất hiện ô nhập password (`input[type="password"]`), thay vào đó xuất hiện input số điện thoại (`input[type="tel"]`, `input#phoneNumber`) hoặc văn bản `"Xác minh rằng đó chính là bạn"` / `"Verify it's you"`.
     - Ý nghĩa: Google phát hiện thiết bị lạ / IP bất thường và yêu cầu SMS hoặc xác minh bảo mật trước khi cho nhập pass.
   - **`WRONG_PASSWORD`**:
     - Xuất hiện sau khi điền pass: DOM chứa `"sai mật khẩu"` / `"wrong password"`.
   - **`ACCOUNT_DISABLED`**:
     - DOM chứa `"tài khoản bị vô hiệu hóa"` / `"account disabled"`.
   - **`LOGIN_SUCCESS`**:
     - URL chuyển hướng sang `myaccount.google.com` hoặc `mail.google.com`.

5. **Lưu Evidence & Cleanup Profile:**
   - Luôn chụp ảnh màn hình hiện trường lưu vào thư mục debug screenshots (`debug_screenshots/<email>.png`).
   - Đóng browser context.
   - Gọi API dọn dẹp đóng và xoá vĩnh viễn profile tạm:
     - `GET /api/v3/profiles/close/{profile_id}`
     - `GET /api/v3/profiles/delete/{profile_id}?mode=2`
