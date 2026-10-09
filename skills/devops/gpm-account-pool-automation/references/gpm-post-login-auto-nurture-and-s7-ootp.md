# GPM Post-Login Auto-Nurture & S7 Security Code OOTP Pipeline

## 1. Bản chất vấn đề
- Khi login Gmail thành công trên GPM Profile, nếu đem nạp OAuth Google SSO (`add_oauth_omniroute.py` hoặc `cron_gpm_oauth_full_pool.py`) ngay lập tức, Google Risk Engine sẽ xếp vào hành vi bất thường (Sensitive Action không có session history / browsing history) -> kích hoạt Phone Checkpoint hoặc rơi vào 72h Cooldown.
- Khi gặp thử thách Google đòi xác minh:
  - Màn hình `challenge/selection`: Cần ưu tiên chọn "Mã bảo mật trên điện thoại" (`data-challengetype="8"`).
  - Màn hình `challenge/ootp`: Bắt buộc trích xuất mã 10 số từ thiết bị Samsung S7 thực tế thay vì điền số điện thoại hay bấm bừa.

## 2. Chuỗi kích hoạt Nuôi tự nhiên (Post-Login Auto-Nurture)
Trong `post_evening_gpm_login_watchdog.py`:
- Sau khi `success = True` và cập nhật `GroupId = 10` (Google Live Ready).
- BẮT BUỘC kích hoạt script nuôi tự nhiên `cron_gpm_gmail_nurture.py` qua tiến trình nền không phong bế:
```python
nurture_script = Path(r"D:\Taadaa\GPM auto\scripts\cron_gpm_gmail_nurture.py")
if nurture_script.exists():
    log(f"[M{mid:02d}] 🚀 Nối kích hoạt script nuôi tự nhiên cho {email}...")
    try:
        subprocess.Popen(
            [PYTHON_EXE, str(nurture_script), "--email", email],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e_nur:
        log(f"[M{mid:02d}] Lỗi kích hoạt nurture cho {email}: {e_nur}")
```
- Tác dụng: Mỗi nick vừa đăng nhập xong sẽ tự động lướt YouTube, đọc báo Google News 90-120s để tích lũy cookie và Trust Score trước khi bốc đi lấy OAuth.

## 3. Tích hợp lấy mã 10 số S7 vào Cron OAuth Feeder
Trong `cron_gpm_oauth_full_pool.py`:
1. Tra cứu `machine_id` và `serial` qua `CredentialLookup.get(email)`.
2. Bắt `challenge/selection`: Click phương thức xác minh mã bảo mật.
3. Bắt `challenge/ootp` hoặc ô input Pin:
   - Gọi `get_s7_security_code(machine_id, serial, email)` thông qua Device Lock trên S7.
   - Điền mã 10 số vào ô Pin và bấm Tiếp theo (`#totpNext`, `#passwordNext`, Enter).
   - Đặt cờ `s7_code_entered = True` để tránh điền lặp.
