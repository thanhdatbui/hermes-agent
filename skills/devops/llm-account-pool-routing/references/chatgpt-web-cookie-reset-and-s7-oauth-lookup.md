# ChatGPT-Web Cookie Reset & Farm S7 OAuth Device Resolution

## 1. ChatGPT-Web Session Renewal Pitfall & Fix
- **Triệu chứng:** Watchdog báo lỗi `Validate fail: HTTP Error 400: Bad Request` khi hồi sinh tài khoản ChatGPT-Web văng cookie.
- **Cơ chế lỗi:**
  1. Khi session cookie hết hạn hoặc bị revoked, script gọi `context.clear_cookies()`.
  2. Nếu không gọi lại `page.goto("https://chatgpt.com/auth/login")` ngay sau khi dọn cookie, Playwright vẫn giữ DOM/state cũ bị hỏng của trang trước. Form nhập email và password không bao giờ xuất hiện.
  3. Hàm kết thúc và trả về `None` (hoặc rỗng).
  4. Nếu hàm validate gửi trực tiếp payload `{"provider": "chatgpt-web", "apiKey": null}` lên OmniRoute `/api/providers/validate`, OmniRoute sẽ trả về `HTTP 400 Bad Request` vì thiếu API key.
- **Quy tắc xử lý:**
  1. Sau `context.clear_cookies()`, bắt buộc nạp lại URL:
     ```python
     context.clear_cookies()
     page.goto("https://chatgpt.com/auth/login", timeout=35000, wait_until="domcontentloaded")
     page.wait_for_timeout(2000)
     ```
  2. Bổ sung guard rỗng ngay đầu hàm `test_connection_valid`:
     ```python
     if not cookie_str or not isinstance(cookie_str, str):
         return False, "EMPTY_SESSION_TOKEN"
     ```

## 2. Farm S7 Device Resolution cho Antigravity OAuth
- **Triệu chứng:** Tài khoản Google bị kẹt tại màn hình duyệt Google Prompt (`challenge/dp`) hoặc đòi mã bảo mật 10 số (`challenge/ootp`), watchdog timeout 90s do không tương tác được với thiết bị S7.
- **Cơ chế lỗi:**
  - Hàm tra cứu thiết bị `get_account_for_email` chỉ quét sheet `Kibe_Farm_S7` của `master_gmail_manager.xlsx`.
  - Các tài khoản Gmail farm thực tế được quản lý và cập nhật tại `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`).
- **Quy tắc tra cứu chuẩn:**
  1. Ưu tiên đọc `taikhoan_dat_v2_updated .xlsx` sheet `Tài Khoản`:
     - Cột A (index 0 / cell 1): Số Máy farm (`mid`)
     - Cột F (index 5 / cell 6): Địa chỉ Gmail (`email`)
     - Cột J (index 9 / cell 10): Device ID / Serial ADB (`serial`)
     - Proxy port: `20000 + mid` (Sing-box port tương ứng với máy)
  2. Fallback an toàn về `master_gmail_manager.xlsx` nếu không tìm thấy trong file cập nhật.
  3. Khi có đủ `mid` và `serial`, watchdog kích hoạt được `approve_s7_google_prompt` và `get_s7_security_code` qua port 7912 (ATX-Agent) mà không bị rơi vào vòng lặp chờ timeout.
