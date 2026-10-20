# Cạm Bẫy Ngắn Mạch ALREADY_SUCCESS & Vòng Lặp Phục Hồi Ảo Trong Pure Google Login (2026-10-20)

## 1. Hiện Tượng & Triệu Chứng
- **Báo cáo đối nghịch:** Watchdog ca đăng nhập (`post_evening_gpm_login_watchdog.py`) báo cáo hàng chục tài khoản thành công (`total_success: 31`), nhưng Báo cáo 6H (`gpm-gmail-nurture-6h-report.py`) ghi nhận số lượt nuôi thực tế là 0 và toàn bộ tài khoản vừa xử lý lập tức văng lại trạng thái `NEEDS_LOGIN`.
- **Dậm chân tại chỗ:** Hàng chục tài khoản (ví dụ 49/77 profile Group 10) bị kẹt vĩnh viễn trong trạng thái `NEEDS_LOGIN` qua nhiều phiên, nhiều ngày mà không có bất kỳ tiến triển nào.

## 2. Nguyên Nhân Gốc Rễ: Ngắn Mạch Phụ Thuộc OmniRoute Cũ
Trong kiến trúc tách biệt Pure Login vs OAuth (`gpm-login-pure-google-signin-and-antigravity-decoupling-20261019.md`), farm chuyển sang chế độ `--login-only` (chỉ đăng nhập Google thuần túy vào Chromium GPM để giữ cookie session, không nạp token Antigravity).

Tuy nhiên, tồn tại khiếm khuyết phân nhánh trong bộ lọc trước đăng nhập:
1. **Kiểm tra `omniroute_success` trước `login_only` trong `run_oauth_s7_pipeline.py`:**
   ```python
   # ĐOẠN CODE LỖI: Nằm trước khi đọc cờ login_only
   if email in status_data.get("omniroute_success", {}):
       logger.info(f"[M{mid:02d}] ⏭️ Bỏ qua {email}: ĐÃ NẠP THÀNH CÔNG VÀO OMNIROUTE!")
       cid = status_data["omniroute_success"][email].get("connection_id")
       return {"mid": mid, "email": email, "status": "ALREADY_SUCCESS", "conn_id": cid}
   ```
   Khi watchdog gọi `python run_oauth_s7_pipeline.py <email> --login-only`, script thấy email đã từng nạp thành công vào OmniRoute (từ nhiều tuần trước), liền trả về ngay `ALREADY_SUCCESS` trong 0.1s mà **hoàn toàn không mở Chromium để đăng nhập Google**.

2. **Watchdog ngộ nhận `ALREADY_SUCCESS` là đăng nhập thành công:**
   Trong `post_evening_gpm_login_watchdog.py`:
   ```python
   success = ((("SUCCESS" in combined ...) or "ALREADY_SUCCESS" in combined))
   ```
   Watchdog thấy `ALREADY_SUCCESS` thì tưởng tài khoản đã có session trong profile GPM, liền:
   - Ghi nhận `total_success += 1`.
   - Cập nhật `nurture_data[email]["status"] = "LOGIN_RECOVERED"`.
   - Lập tức kích hoạt tiến trình nuôi ngầm: `cron_gpm_gmail_nurture.py --email <email>`.

3. **Nurture mở profile phát hiện "chưa login" và khóa cooldown 24h:**
   Trình nuôi `cron_gpm_gmail_nurture.py` mở profile GPM thật lên, kiểm tra session cookie Google thấy `0 token`:
   `[WARNING] CẢNH BÁO: Profile chưa có acc Google hoặc mất session (chỉ thấy 0 token). Dừng nuôi để tránh lãng phí!`
   Nó lập tức đánh dấu `status = "NEEDS_LOGIN"` và đẩy tài khoản vào chu kỳ cách ly `24h cooldown` (`is_profile_in_needs_login_cooldown`).

4. **Hệ quả Vòng Lặp Ma (Phantom Recovery Loop):**
   Mỗi ca rảnh, Watchdog chọn tài khoản ➔ `run_oauth_s7_pipeline.py` bỏ qua và trả `ALREADY_SUCCESS` ➔ Watchdog tưởng thành công báo cáo xanh ➔ Nurture mở ra thấy 0 token đẩy lại vào `NEEDS_LOGIN` ➔ Ngâm 24h ➔ Ca hôm sau lặp lại. Toàn bộ farm không đăng nhập được thêm 1 acc nào.

## 3. Quy Tắc & Tiêu Chuẩn Sửa Chữa (Invariants)
1. **Decoupling Hoàn Toàn Trong `--login-only`:**
   - Khi cờ `--login-only` được truyền vào, **TUYỆT ĐỐI BỎ QUA** mọi kiểm tra liên quan đến OmniRoute (`omniroute_success`, `connection_id`, `antigravity`).
   - Việc OmniRoute có token hay không **KHÔNG ĐỒNG NGHĨA** với việc GPM profile có session cookie Google sống.
   - BẮT BUỘC đặt parsing cờ `login_only` lên ĐẦU HÀM `process_account()` trước mọi bước kiểm tra trạng thái cache.
2. **Loại Bỏ `ALREADY_SUCCESS` Khỏi Watchdog Pure Login:**
   - Trong `post_evening_gpm_login_watchdog.py`, khi chạy luồng `--login-only`, CHỈ chấp nhận kết quả thành công khi có bằng chứng telemetry DOM thực tế:
     `login_only_success` (hoặc URL về `myaccount.google.com` và avatar hiển thị `is_visible() == True`).
   - CẤM TUYỆT ĐỐI coi `ALREADY_SUCCESS` là tín hiệu đăng nhập thành công cho GPM profile.
3. **Reset State Sau Khi Vá Code:**
   - Sau khi vá bug ngắn mạch, phải xóa các timestamp `last_checked` đang ngâm 24h cooldown của các tài khoản bị văng ảo để watchdog ca kế tiếp (21:30) có thể mở browser đăng nhập thực tế.
