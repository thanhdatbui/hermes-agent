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

## 5. Thực Thi Cụ Thể Trong Mã Nguồn (--login-only & Watchdog Decoupling)
1. **Tích hợp cờ `--login-only` trong `scripts/run_oauth_s7_pipeline.py`:**
   - Bắt tham số qua `acc.get("login_only")` hoặc `--login-only` trong `sys.argv`.
   - `auth_url` chuyển hướng thẳng về `https://accounts.google.com/ServiceLogin?hl=vi`.
   - Vòng lặp quan sát tự động break ngay khi URL đạt `myaccount.google.com` (đánh dấu `captured_code = "LOGIN_ONLY_SUCCESS"`).
   - Thoát hàm và trả về `status: SUCCESS`, hoàn toàn bỏ qua bước gọi API OmniRoute `/api/oauth/antigravity/exchange`, không gán proxy vào connection Antigravity và không sync models.
2. **Cập nhật Watchdog `post_evening_gpm_login_watchdog.py`:**
   - Hàm `run_login()` truyền tường minh `"--login-only"` vào tham số dòng lệnh của `GPM_SCRIPT`.
   - Gỡ bỏ dòng đếm `Antigravity Pool: ... accounts LIVE trên OmniRoute (:20129)` và sửa nhãn `chờ OAuth` thành `Profile sẵn Google Session` trong `_format_summary_report()`.
   - Các profile đã có sẵn session cookie Google (`session_emails`) và không bị báo `NEEDS_LOGIN` được giữ nguyên trong Group 10 để cron nuôi định kỳ tiếp quản, không cố mở lại để đi OAuth.
3. **Vô hiệu hóa nhánh hồi sinh Antigravity trong `cron_chatgpt_web_pool_watchdog.py`:**
   - Đặt `ag_broken = []` để triệt tiêu việc tự động mở GPM profile hồi sinh OAuth Antigravity định kỳ mỗi 6 giờ.

## 6. Tiêu Chuẩn Thẩm Định Closeout Gate & Khắc Phục Khiếm Khuyết Test (Reviewer Sol High Feedback)
Khi nghiệm thu luồng Pure Login qua `closeout_gate.py`, Reviewer độc lập (Sol High) đòi hỏi các tiêu chí khắt khe sau để đạt điểm $\ge 85$:
1. **Xác nhận thành công bằng Cơ chế Kép (Double Verification) & Chống False Positive:**
   - Không chỉ dựa vào URL `myaccount.google.com` (dễ dính false positive từ redirect dở dang).
   - Kết hợp kiểm tra phần tử DOM định danh người dùng:
     ```python
     avatar_selectors = '[aria-label*="Google Account"], [aria-label*="Tài khoản Google"]'
     ```
   - **Bắt buộc kiểm tra hiển thị thực tế:** Phần tử avatar phải tồn tại và `is_visible() == True` (`count > 0 and loc.is_visible()`). Tuyệt đối không chỉ kiểm tra `count > 0` vì avatar có thể tồn tại ở trạng thái ẩn/DOM rác trên form đăng nhập chưa hoàn tất.
2. **Telemetry có cấu trúc Đầy Đủ Cả Success & Failure (Structured Telemetry):**
   - Sự kiện thành công: `log_telemetry_metric("login_only_success", {"mid": mid, "email": email, "url": cur_url})`
   - Sự kiện thất bại / timeout: `log_telemetry_metric("login_only_failed", {"mid": mid, "email": email, "reason": "timeout"})` kèm log `[TELEMETRY] correlation_id={cid} event=login_only_failed reason=timeout` ra stderr để observability giám sát tỷ lệ rớt login mà không làm rò rỉ cookie hay credentials.
3. **Bộ Negative Unit Tests Bắt Buộc (Chống Ảo Giác Code Coverage):**
   - Test case 1: Điều hướng vào landing URL `myaccount.google.com` ➔ thành công, không gọi API OmniRoute authorize/exchange.
   - Test case 2: Điều hướng vào challenge URL nhưng xuất hiện Avatar hiển thị (`count == 1, is_visible == True`) ➔ thành công, ghi nhận metric telemetry `login_only_success`.
   - Test case 3 (Negative - Avatar ẩn): Avatar có trong DOM nhưng `is_visible() == False` ➔ không được nhận diện thành công, loop chạy đến khi timeout và phát telemetry `login_only_failed`.
   - Test case 4 (Negative - Không có Avatar): `count == 0` trên challenge URL ➔ timeout và phát telemetry `login_only_failed`.
   - Test case 5 (Negative - Lỗi DOM): `loc.is_visible()` văng ngoại lệ `RuntimeError("DOM disconnected")` ➔ xử lý an toàn không crash script, timeout và phát telemetry `login_only_failed`.
4. **Hạ Tầng Điều Phối Khi Chạm Claude Quota Guard:**
   - Khi Claude Quota 5 giờ $\ge 85\%$ (ví dụ 88%), `claude_quota_guard.py` tự động chặn.
   - Dispatch Worker tự động kích hoạt Tier 2 Fallback: Antigravity CLI (`gemini-3.8-flash-medium` trên pool 22 accounts xoay vòng).
   - Nếu Agy CLI timeout hoặc kẹt mà Coordinator đã có exact diff O(1) chuẩn hóa (<= 2 files, <= 30 dòng, 1 focused test), Coordinator được kích hoạt quyền L2 Emergency Surgery commit tiền tố `[L2-surgery]` và nghiệm thu qua test suite cục bộ.


