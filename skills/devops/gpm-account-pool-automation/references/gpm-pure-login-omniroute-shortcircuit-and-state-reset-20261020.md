# Cạm Bẫy Ngắn Mạch OmniRoute Khi Pure Google Login & Khắc Phục Vòng Lặp Đăng Nhập Ảo (2026-10-20)

## 1. Hiện Tượng & Triệu Chứng Lỗi
- **Triệu chứng:** Báo cáo định kỳ 6H (`gpm-gmail-nurture-6h-report`) báo cáo `Đã nuôi trong 6h qua: 0 lượt`, `Tài khoản giữ session ấm: 36.4%` (28/77 profile) và danh sách `Tổng acc đang chờ re-login (Group 10): 49 acc` dậm chân tại chỗ qua nhiều phiên không hề suy giảm.
- **Nghịch lý telemetry:**
  - Watchdog ca đăng nhập (`post_evening_gpm_login_watchdog.py`) báo cáo ca Sáng và Chiều thành công hàng chục acc (`total_success: 31`).
  - Nhưng ngay sau đó, watchdog nuôi (`cron_gpm_gmail_nurture.py`) mở profile lên kiểm tra thì phát hiện `0 token` (mất session), lập tức đẩy lại vào `NEEDS_LOGIN` và áp đặt cooldown 24h.

## 2. Phân Tích Root Cause (False-Positive Short-Circuit Loop)
1. **Ngắn mạch kiểm tra OmniRoute ở đầu pipeline (`run_oauth_s7_pipeline.py`):**
   - Trước khi bóc tách cờ `--login-only`, script đọc `STATUS_JSON` (`oauth_pipeline_status.json`).
   - Nếu email từng nạp OmniRoute trong quá khứ (`email in status_data["omniroute_success"]` — thực tế 45/49 acc dính điều kiện này), script in log `⏭️ Bỏ qua {email}: ĐÃ NẠP THÀNH CÔNG VÀO OMNIROUTE!` và trả về `status: "ALREADY_SUCCESS"` ngay lập tức mà không mở Chromium đăng nhập Google.
2. **Ngộ nhận thành công tại Watchdog (`post_evening_gpm_login_watchdog.py`):**
   - Biểu thức `success = ((("SUCCESS" in combined ...) or "ALREADY_SUCCESS" in combined))` ngộ nhận chuỗi `ALREADY_SUCCESS` là đăng nhập thành công.
   - Watchdog cập nhật `nurture_data[email]["status"] = "LOGIN_RECOVERED"`, ghi nhận `recovered_date = today_str`, và kích hoạt ngầm `cron_gpm_gmail_nurture.py --email <email>`.
3. **Nurture đẩy ngược lại vào `NEEDS_LOGIN` và kẹt bẫy 24h Cooldown:**
   - Profile thực tế chưa từng được đăng nhập Google (0 token session).
   - Nurture script cập nhật `status = "NEEDS_LOGIN"` và cập nhật `last_checked = now`.
   - Trong các ca tiếp theo, watchdog bỏ qua acc vì `recovered_date == today_str` hoặc `em in seen_emails`, còn nurture bỏ qua vì `is_profile_in_needs_login_cooldown` (24h), tạo thành vòng lặp đóng băng vĩnh viễn.

## 3. Quy Chuẩn Kỹ Thuật Bắt Buộc (Pure Login Decoupling Invariant)
1. **Bypass 100% OmniRoute Tracker khi chạy `--login-only`:**
   - Bắt buộc tính toán cờ `login_only` ngay từ đầu hàm `process_account(acc)`:
     ```python
     login_only = bool(acc.get("login_only", False) or os.environ.get("LOGIN_ONLY") == "1" or "--login-only" in sys.argv)
     ```
   - Chặn tuyệt đối việc kiểm tra trạng thái OmniRoute khi đang ở chế độ login thuần:
     ```python
     if not login_only and os.path.exists(STATUS_JSON):
         # Kiểm tra omniroute_success, cooldown_7days...
     ```
2. **Loại trừ `ALREADY_SUCCESS` khỏi điều kiện thành công của Watchdog:**
   - Watchdog đăng nhập GPM chỉ chấp nhận thành công khi Chromium hoàn tất quy trình và vào tới `myaccount.google.com` (có avatar định danh hiển thị):
     ```python
     success = (
         "SUCCESS" in combined and "LAUNCH_FAILED" not in combined 
         and "EXCHANGE_FAILED" not in combined and "ALREADY_SUCCESS" not in combined
     )
     ```
3. **Quy trình Khôi phục Trạng thái Kẹt (State Sanitization Runbook):**
   - Khi phát hiện vòng lặp ảo, bắt buộc làm sạch cả 2 file state:
     - `gpm_gmail_nurture_state.json`: Xóa `recovered_date`, `recovered_at`, và đặt `last_checked = 0` cho toàn bộ tài khoản `NEEDS_LOGIN`.
     - `post_evening_gpm_login_state.json`: Reset `processed = []`, `proxy_count = {}`, `total_success = 0`, `total_fail = 0` để ca tiếp theo được phép nhận lại danh sách candidate.
