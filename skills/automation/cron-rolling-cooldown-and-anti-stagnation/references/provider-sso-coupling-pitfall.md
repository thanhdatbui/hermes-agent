# Provider SSO Coupling Pitfall in Multi-Domain Account Pool Auto-Feeders

## 1. Triệu chứng & Hiện trường lỗi
- Trong watchdog/cron nạp tài khoản LLM pool (`cron_auto_feed_chatgpt_pool.py`), khi ưu tiên xử lý tài khoản Hotmail trước Gmail, batch 10 tài khoản Hotmail đều báo thất bại và bị phạt `cooldown 12h`.
- WinRT OCR trên ảnh debug (`chatgpt_proof_<user>.png`) cho thấy trình duyệt đang đứng tại màn hình Google Sign-in:
  `"Đăng nhập bằng Google / Email / Tiếp tục tới OpenAI / Tạo tài khoản"`.

## 2. Nguyên nhân cốt lõi (Provider SSO Coupling)
- Handler xử lý khi phiên hết hạn được viết cứng cho Google SSO (`js_click_google`).
- Tài khoản `@hotmail.com` không có session Google lưu sẵn trong profile GPM. Khi click `Continue with Google`, trang chuyển sang `accounts.google.com`, script quét `[data-identifier]` để tìm địa chỉ Hotmail và không bao giờ tìm thấy.
- Kết quả: Vòng lặp chờ 35 giây cạn kiệt, không lấy được `session-token`, tài khoản bị đánh dấu lỗi và đẩy vào danh sách phạt cooldown oan.
- Ngược lại, các nick Hotmail đã có sẵn `__Secure-next-auth.session-token` trong cookie thì pass vì script đọc cookie thành công ở bước pre-check trước khi chạm tới SSO.

## 3. Quy chuẩn khắc phục & Khóa an toàn
1. **Phân luồng xác thực theo Provider Domain:**
   - Chỉ kích hoạt `js_click_google` khi `acc['email'].endswith('@gmail.com')`.
   - Với `@hotmail.com`, nếu thiếu session cookie, cấm click Google SSO; ghi nhận trạng thái yêu cầu auth riêng (Direct Email/Password + OTP qua Graph API) hoặc fail-fast nhả profile.
2. **Bảo toàn danh sách Cooldown:**
   - Khi phát hiện lỗi kiến trúc mismatch provider, phải clear danh sách cooldown (`failed_candidates_cooldown.json`) để các nick không bị phạt oan 12h.

3. **Mẫu code chuẩn hóa Fail-Fast & Unit Test:**
   - Code logic trong `rescue_single_account()`:
     ```python
     if "hotmail" in email.lower():
         logger.info(f"[{email}] Hotmail bỏ qua Google SSO.")
         res["error"] = "Hotmail bo qua Google SSO"
         return res  # Đi thẳng vào finally dọn dẹp profile, không mở SSO
     ```
   - Unit test focused: Cần mock `sync_playwright` và context cookies rỗng để verify `res['success'] == False` và `res['error'] == 'Hotmail bo qua Google SSO'` mà không gọi `js_click_google`.
