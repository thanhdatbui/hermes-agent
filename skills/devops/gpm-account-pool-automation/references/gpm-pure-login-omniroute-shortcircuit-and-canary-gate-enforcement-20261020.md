# Cạm Bẫy Ngắn Mạch OmniRoute Trong Pure Google Sign-in & Cơ Chế Ép Canary Cho GPM (2026-10-20)

## 1. Hiện Tượng & Triệu Chứng Bế Tắc (The Phantom Success Loop)
- **Triệu chứng:** Báo cáo watchdog ca sáng/chiều (`post_evening_gpm_login_watchdog.py`) báo `total_success: 31`, nhưng báo cáo 6h (`gpm-gmail-nurture-6h-report`) ghi nhận số lượt nuôi thực tế là `0` và 49/77 tài khoản Group 10 vẫn kẹt cứng ở trạng thái `NEEDS_LOGIN`.
- **Phản ánh từ Operator:** *"tao thấy lỗi cả đống k tiến triển gì so vs các phiên trc"*, *"ủa mà t bỏ đi oauth omni tài khoản google r mà"*, *"T nhớ có gate ép run canary mà"*.

---

## 2. Root Cause Analysis (RCA): Ngắn Mạch Logic Trạng Thái Cũ
1. **Bẫy kiểm tra OmniRoute trước `login_only` (`run_oauth_s7_pipeline.py`):**
   - Dù cờ `--login-only` đã được truyền từ watchdog, nhưng đoạn code tại đầu hàm `process_account(acc)` vẫn đọc `oauth_pipeline_status.json`.
   - Với 45/49 tài khoản từng hoàn tất OAuth Antigravity trước ngày 19/10, script thấy email nằm trong `status_data.get("omniroute_success")` liền in:
     `⏭️ Bỏ qua {email}: ĐÃ NẠP THÀNH CÔNG VÀO OMNIROUTE!`
     và lập tức trả về `status: "ALREADY_SUCCESS"` trong 0.1 giây mà không hề mở Chromium hay chạm vào GPM profile.
2. **Watchdog ngộ nhận và khóa oan tài khoản trong ngày:**
   - `post_evening_gpm_login_watchdog.py` có điều kiện:
     `success = (("SUCCESS" in combined ...) or "ALREADY_SUCCESS" in combined)`
   - Nhận `ALREADY_SUCCESS`, watchdog ghi nhận `✓ SUCCESS`, set `recovered_date = today_str` (khiến tài khoản bị loại khỏi các ca chạy tiếp theo trong ngày) và gọi ngầm `cron_gpm_gmail_nurture.py --email <email>`.
3. **Nurture mở profile thấy 0 token và kích hoạt cooldown 24h:**
   - Trình nuôi mở profile GPM thấy mất session Google thật (0 token), đánh dấu `NEEDS_LOGIN` và áp đặt `is_profile_in_needs_login_cooldown` (24 giờ).
   - Vòng lặp giả mạo lặp lại vô tận qua các ca mà 0 tài khoản nào được đăng nhập thật.

---

## 3. Khắc Phục Triệt Để (Decoupling & Strict Verification)

1. **Khóa chặt `login_only` trước mọi tracker OmniRoute:**
   - Tính toán `login_only` ngay tại dòng đầu của `process_account`:
     ```python
     login_only = bool(acc.get("login_only", False) or os.environ.get("LOGIN_ONLY") == "1" or "--login-only" in sys.argv)
     ```
   - Chặn tuyệt đối việc kiểm tra file trạng thái OmniRoute khi đang ở chế độ login thuần túy:
     ```python
     if not login_only and os.path.exists(STATUS_JSON):
         ...
     ```
2. **Triệt tiêu `ALREADY_SUCCESS` trong watchdog:**
   - Điều kiện thành công trong `run_login()` bắt buộc phải có `SUCCESS` thật và cấm chứa `ALREADY_SUCCESS`:
     ```python
     success = (
         "SUCCESS" in combined and "LAUNCH_FAILED" not in combined
         and "EXCHANGE_FAILED" not in combined and "ALREADY_SUCCESS" not in combined
     )
     ```
3. **Reset State Sau Khi Vá:**
   - Xóa bỏ `recovered_date` và reset `last_checked` trên `gpm_gmail_nurture_state.json` cho toàn bộ tài khoản bị kẹt cooldown giả.
   - Reset danh sách `processed` trong `post_evening_gpm_login_state.json` để ca tối tự động kéo acc ra đăng nhập thật.

---

## 4. Cơ Chế Ép Canary Cho GPM Tại `done_gate.py` (Mechanical Enforcement)

- **Trước sửa đổi:** `done_gate.py` chỉ định nghĩa `AUTOMATION_REPOS` cho các repo Android Phone Farm (`tiktok-*`, `register gmail`, `automation-core`), khiến các task fix code trên `GPM auto` bị nhận diện nhầm là `general` và bypass qua `GATE-PASS(bypass): Non-automation task`.
- **Sau sửa đổi:**
  1. Thêm `GPM_REPOS = ("gpm auto", "auto-gpm")` vào `AUTOMATION_REPOS`.
  2. Bổ sung `is_gpm_repo()` và `is_gpm_available()` (thăm dò TCP tới `127.0.0.1:19995` trong 2s).
  3. Phân nhánh cưỡng chế:
     - Nếu có chứng cứ canary hợp lệ (`--canary-file` hoặc receipt): `GATE-PASS: Canary verified for GPM.`
     - Nếu thiếu chứng cứ và GPM API khả dụng: `GATE-FAIL: GPM automation code fix BAT BUOC phai chay Canary tren GPM profile that truoc khi bao DONE.` (Exit code: 1, chặn đứng declare DONE).
     - Nếu GPM API không khả dụng: `GATE-PASS(deferred): GPM khong kha dung, tam hoan Canary GPM.`
  4. Đã bảo vệ bằng 9 unit tests trong `D:/Taadaa/tools/tests/test_done_gate.py` (100% pass).
