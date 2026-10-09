# ChatGPT Google SSO Onboarding via GPM v3 & Playwright CDP

Tài liệu chuẩn hóa flow tự động đăng nhập / onboarding tài khoản ChatGPT (`https://chatgpt.com`) bằng Google Account có sẵn trên profile GPMLogin Local API v3.

## 1. Kiến trúc luồng thực thi
1. **Khởi động GPM Profile qua Local API v3:**
   - Endpoint: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
   - Trích xuất: `remote_debugging_address` (hoặc `selenium_remote_debug_address`).
2. **Kết nối Playwright CDP:**
   - Dùng Python: `sync_playwright().chromium.connect_over_cdp(cdp_endpoint)`
   - Duyệt các tabs / pages đang mở hoặc tạo page mới hướng tới `https://chatgpt.com`.
3. **Thực hiện SSO với Google:**
   - Nhận diện nút `Continue with Google` (hoặc bản dịch tiếng Việt `Tiếp tục với Google`).
   - Xử lý Google OAuth redirect / popup: chọn tài khoản Gmail đã có session sẵn trong profile GPM.
4. **Xử lý Onboarding & Checkpoints:**
   - **Tell us about you (Họ tên & Ngày sinh):**
     - Điền tên hiển thị và ngày sinh hợp lệ (> 18 tuổi, định dạng `DD/MM/YYYY` hoặc `MM/DD/YYYY` theo locale DOM).
   - **Cloudflare Turnstile:**
     - Đợi iframe turnstile hoặc click checkbox giải captcha nếu xuất hiện.
   - **Phone verification checkpoint:**
     - Nếu xuất hiện trường nhập số điện thoại hoặc yêu cầu mã SMS, không để tiến trình bị treo.
     - Lập tức chụp ảnh màn hình lưu vào folder debug (vd: `debug_screenshots/chatgpt_<email>.png`).
     - Đánh dấu trạng thái `PHONE_VERIFICATION_REQUIRED` và thoát luồng con thành công có kiểm soát.
5. **Đóng Profile giải phóng tài nguyên:**
   - Đảm bảo luôn nằm trong khối `finally`:
   - Endpoint: `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`.
