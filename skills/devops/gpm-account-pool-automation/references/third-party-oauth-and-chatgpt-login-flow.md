# Quy trình Tự động Đăng nhập / Khởi tạo Tài khoản Dịch vụ Thứ 3 (ChatGPT, OpenAI, v.v.) qua Google OAuth trên GPM Profile

## 1. Tổng quan & Bối cảnh
Khi các profile GPM đã đăng nhập sẵn tài khoản Gmail/Google, các dịch vụ web bên thứ ba (như ChatGPT, Claude, Discord, v.v.) hỗ trợ đăng nhập qua Single Sign-On (SSO / Continue with Google). Việc tự động hóa flow này cần tận dụng trực tiếp session Google có sẵn trong profile GPM thay vì phải nhập lại mật khẩu và giải checkpoint tài khoản Google.

## 2. Kiến trúc Thực thi chuẩn (Playwright CDP + GPM API v3)
1. **Khởi động Profile GPM:**
   - Endpoint: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
   - Trích xuất: `remote_debugging_address` (vd: `127.0.0.1:xxxxx`).
2. **Kết nối Playwright qua CDP:**
   ```python
   from playwright.sync_api import sync_playwright

   with sync_playwright() as p:
       browser = p.chromium.connect_over_cdp(f"http://{remote_addr}")
       context = browser.contexts[0]
       page = context.pages[0] if context.pages else context.new_page()
   ```
3. **Điều hướng & Kích hoạt OAuth:**
   - Mở `https://chatgpt.com` (hoặc `https://chatgpt.com/auth/login`).
   - Bấm nút "Log in" / "Đăng nhập".
   - Tại trang xác thực OpenAI (`auth.openai.com`), bấm "Continue with Google" / "Tiếp tục với Google" (`button[data-provider="google"]`).
4. **Xử lý Google Account Chooser:**
   - Vì trình duyệt đã có cookie/session Google, Google sẽ hiển thị danh sách tài khoản hoặc trang xác nhận chia sẻ thông tin.
   - Bấm chọn tài khoản Gmail tương ứng hoặc bấm nút "Tiếp tục" / "Continue" / "Cho phép".
5. **Xử lý Onboarding & Checkpoint bên thứ ba (ChatGPT/OpenAI):**
   - **Màn hình "Tell us about you":** Điền họ tên và ngày sinh hợp lệ (đảm bảo độ tuổi $\ge 18$, ví dụ: `15/08/1998`).
   - **Cloudflare Turnstile:** Đợi 10–15s để anti-detect fingerprint của GPM tự vượt qua hoặc click vào checkbox xác minh nếu hiển thị.
   - **Xác minh số điện thoại (Phone Verification):** Nếu dịch vụ yêu cầu xác minh SĐT, script KHÔNG được treo mà phải chụp ảnh màn hình lưu vào `debug_screenshots/` và ghi nhận trạng thái `PHONE_VERIFICATION_REQUIRED`.
6. **Nghiệm thu & Dọn dẹp:**
   - Chụp ảnh màn hình giao diện chat đã đăng nhập thành công (`chatgpt_<email>.png`).
   - Luôn đặt lệnh đóng profile trong khối `finally`:
     - `browser.close()`
     - `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`

## 3. Bài học Điều phối Worker Subagent (Chống cháy ngân sách)
- **Cạm bẫy:** Repo automation GPM chứa nhiều script monolith lớn (như `run_oauth_s7_pipeline.py` > 1.100 dòng). Nếu dispatch worker với goal chung chung ("tự phân tích codebase và thực thi"), worker sẽ dùng hết ngân sách (15 calls) để đọc file và thử vá nhầm file cũ.
- **Kỷ luật điều phối:** Coordinator phải soạn Patch Contract đóng:
  1. Chỉ định rõ đường dẫn script cần tạo mới (vd: `D:/Taadaa/GPM auto/scripts/chatgpt_gpm_login.py`).
  2. Cung cấp trực tiếp metadata 3 profile (ID, Email, Proxy port, API URL).
  3. Yêu cầu worker đi thẳng vào `write_file` tạo script -> chạy terminal bằng python môi trường chuẩn (`D:/Taadaa/python-envs/automation/Scripts/python.exe`) -> kiểm tra output JSON & ảnh screenshot -> báo cáo kết quả.
