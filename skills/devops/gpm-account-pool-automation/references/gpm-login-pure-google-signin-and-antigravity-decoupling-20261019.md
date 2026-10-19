# Kỷ Luật Tách Biệt Pure Google Sign-in và Dừng OAuth Antigravity Trên GPM Farm (2026-10-19)

## 1. Bối Cảnh & Chỉ Thị Tối Cao Của Farm
- **Chỉ thị:** Dừng toàn bộ các cron job và luồng đi OAuth Antigravity trên toàn bộ farm tài khoản GPM.
- **Mục tiêu vận hành hiện tại:** **CHỈ LOGIN THUẦN TÚY RỒI NUÔI (Pure Login -> Nurture)**.
  1. Login Google vào GPMLogin profile để lưu session/cookie Google.
  2. Nối tiếp sang kịch bản nuôi tự nhiên định kỳ (`cron_gpm_gmail_nurture.py`: xem YouTube, đọc Google News, tìm kiếm Google Search).
  3. TUYỆT ĐỐI KHÔNG đi OAuth Antigravity (Google Cloud Developer API).

## 2. Rủi Ro Nghiệp Vụ Của Việc Lồng Ghép OAuth Antigravity Vào Pha Login
- **Nguyên lý Google Risk Engine:**
  - Gmail sau khi ngâm trên Samsung S7 (7+ ngày) khi đưa lên PC qua trình duyệt Chromium GPMLogin (dù cùng proxy/port) vẫn là một **Thiết bị mới toanh (New Device Fingerprint)**.
  - Khi login thành công qua 2FA TOTP, tài khoản mới chỉ vừa đặt chân lên thiết bị mới.
  - NẾU trong Session 1 hoặc ngay khi vừa login mà cú click đầu tiên lại là cấp quyền **Google Cloud Platform / Cloud Developer API (Antigravity OAuth)**:
    -> Hệ thống Risk Engine của Google sẽ kích hoạt rule báo động đỏ: `New Device Anomaly + Developer Privilege Escalation`.
    -> Tỷ lệ tài khoản bị checkpoint khắt khe (bắt xác minh số điện thoại `challenge/iap`, vô hiệu hóa tài khoản `account disabled`, hoặc chết chùm) lên tới > 90%.

## 3. Cạm Bẫy Mã Nguồn Ngầm (Hidden Leaks) Đã Phát Hiện
Dù 2 cron chuyên trách Antigravity đã tạm dừng từ 04/10:
- `gpm-oauth-full-pool-feeder` (`8ce4b722772f`): PAUSED.
- `gpm-oauth-pool-6h-report` (`55599d8b1551`): PAUSED.

Nhưng trong codebase vẫn còn tồn tại 2 điểm rò rỉ ngầm gọi OAuth Antigravity:
1. **`post_evening_gpm_login_watchdog.py` (chạy qua `gpm-gmail-login-shifts-watchdog`):**
   - Hàm `run_login()` gọi script `run_oauth_s7_pipeline.py`.
   - Script `run_oauth_s7_pipeline.py` không mở trang đăng nhập Google thuần túy mà mở URL `authUrl` của Antigravity (`/api/oauth/antigravity/authorize`).
   - Khi đăng nhập xong, Playwright tự động click nút "Cho phép / Allow / Tiếp tục" để bắt code và exchange lấy token Antigravity nạp lên OmniRoute.
   - **Hậu quả:** Tưởng rằng chỉ login GPM nhưng thực chất là ép tài khoản đi OAuth Antigravity ngay trong ngày đầu tiên.
2. **`cron_chatgpt_web_pool_watchdog.py` (chạy qua `chatgpt-web-pool-healer-watchdog` mỗi 6h):**
   - Vẫn chứa logic quét các connection `antigravity` bị broken và mở profile GPM gọi `perform_antigravity_oauth` để "hồi sinh".

## 4. Chuẩn Hóa Kiến Trúc Pure Google Login
Quy trình Login chuẩn cho mọi script GPM:
1. **URL điều hướng:** Sử dụng URL đăng nhập Google chuẩn:
   `https://accounts.google.com/signin/v2/identifier?flowName=GlifWebSignIn&flowEntry=ServiceLogin`
   (Tuyệt đối KHÔNG trỏ vào OAuth consent URL của bất kỳ ứng dụng thứ 3 nào).
2. **Điền thông tin:**
   - Email -> Password.
   - TOTP 2FA từ Excel / S7 (nếu có yêu cầu).
   - Recovery email (nếu có challenge).
   - Bấm "Lưu mật khẩu / Save password" hoặc bỏ qua prompt "Để sau / Not now".
3. **Xác nhận thành công (Fail-closed):**
   - Kiểm tra URL chuyển về `myaccount.google.com` hoặc có phần tử avatar `a[aria-label*="Google Account"]`.
   - Lưu session cookie Google thành công vào profile GPM (`profile_data.db` cập nhật `GroupId = 10`).
   - Đóng profile sạch sẽ.
4. **Bàn giao sang Nurture:**
   - Kích hoạt hoặc để cron định kỳ `cron_gpm_gmail_nurture.py` tiếp quản nuôi tài khoản theo tỷ lệ 50% YouTube, 30% News/Search, 20% hỗn hợp.
