# Cạm Bẫy Phân Loại Màn Hình "Đặt Lại Mật Khẩu" & Phòng Chống Watchdog Spam Alert

## 1. Bối cảnh & Triệu chứng lỗi (Root Cause từ Sự cố Máy 40 - 2026-09-25)
- Khi khôi phục tài khoản không mật khẩu (passwordless / pass ảo) qua cờ `--otp-only`, script fallback chọn **"Quên mật khẩu?"** -> **"Email"**.
- TikTok chuyển sang màn hình **"Đặt lại mật khẩu"** với layout:
  - Header / Tiêu đề: *"Đặt lại mật khẩu"*
  - Subtitle: *"Bạn sẽ nhận được mã xác minh qua email"*
  - EditText: Ô nhập email (hint: *"Nhập email"* / *"Địa chỉ email"*)
  - Nút: *"Tiếp tục"*
- **Bẫy kích hoạt nhầm (False Positive OTP Screen):**
  Cụm từ *"mã xác minh"* trong subtitle vô tình kích hoạt bộ lọc từ khóa `OTP_HINTS` (`"ma xac minh"`).
- **Hậu quả dây chuyền nghiêm trọng:**
  1. `drive_login_screens` tưởng app đã chuyển sang màn hình điền mã OTP nên lập tức kích hoạt `handle_tiktok_email_otp`.
  2. Script truy vấn hòm thư lấy mã OTP cũ hoặc mã chưa gửi, sau đó gọi `enter_otp_code`.
  3. `enter_otp_code` thấy EditText duy nhất trên màn hình (vốn là ô nhập Email) và điền chuỗi 6 chữ số vào đó.
  4. TikTok từ chối với lỗi đỏ: *"Nhập địa chỉ email hợp lệ"*. Flow kẹt cứng trên màn hình này cho đến khi cạn timeout (480s).
  5. Đồng thời, lỗi import nhầm `from social_reg_v1 import fill_existing_email_and_continue` (hàm này nằm ở `tiktok_login_v1.py`) gây văng exception.
  6. Nếu script cứu hộ được cấu hình chạy qua cron với `deliver: origin` lặp lại mỗi 5 phút, mỗi lần văng exception script sẽ chụp ảnh và spam alert `MEDIA:` liên tục về Telegram DM của User.

---

## 2. Kiến trúc Khắc phục & Điều Kiện Phân Loại Chuẩn (Production Invariant)

### A. Phân biệt rõ màn hình Form Email "Đặt lại mật khẩu" vs Màn hình Nhập Mã OTP thật:
Trước khi kiểm tra `OTP_HINTS` trong `drive_login_screens`:
```python
if any(h in flat for h in OTP_HINTS):
    # Kiểm tra nếu màn hình là form 'Đặt lại mật khẩu' đang yêu cầu nhập email chứ chưa phải ô nhập mã OTP
    if any(k in flat for k in ["dat lai mat khau", "reset password", "nhap email", "nhap dia chi email"]) and "tiep tuc" in flat:
        log(f"   [reset-pwd] Form Đặt lại mật khẩu yêu cầu email, điền email {email}...")
        fill_existing_email_and_continue(device_id, email, stt=stt)
        time.sleep(D_LONG)
        continue

    # Chỉ khi app đã thực sự chuyển sang màn hình kiểm tra email / 6 ô OTP thì mới vào flow lấy OTP
    handle_tiktok_email_otp(device_id, email, account["mail_pass"], stt=stt)
    time.sleep(D_LONG)
    continue
```

### B. Chốt chặn trong hàm `enter_otp_code`:
Trong `social_reg_v1.py`, hàm `enter_otp_code` bắt buộc loại trừ mọi EditText có hint liên quan đến email hoặc tài khoản:
```python
nodes = list_edittext_nodes(xml)
otp_nodes = [
    n for n in nodes 
    if (n["x2"] - n["x1"]) < 200 
    and not any(h in (n.get("hint") or "").lower() for h in ["email", "dia chi email", "tai khoan"])
]
```

### C. Quy tắc Chống Spam Alert từ Cron Watchdog (Taadaa Farm Anti-Spam):
1. **Tuyệt đối cấm `deliver: origin` cho Cron tần suất cao (`*/5 * * * *`):**
   - Mọi watchdog chạy nền tự động bắt buộc cấu hình `deliver: local` hoặc gửi về channel telemetry chuyên dụng.
   - Chỉ dùng `deliver: origin` cho các thông báo tổng kết ngày (1-2 lần/ngày) hoặc watchdog thực sự có bộ lọc silent khi không có thay đổi.
2. **Circuit Breaker cho Script Cứu hộ Tự Động:**
   - Watchdog đơn máy phải có biến đếm số lần thất bại (Max Retries = 2 hoặc 3).
   - Khi thất bại quá ngưỡng, script phải tự tạo flag dừng hoặc xóa/pause job, tuyệt đối không loop vĩnh viễn gây nghẽn ADB và spam User.
