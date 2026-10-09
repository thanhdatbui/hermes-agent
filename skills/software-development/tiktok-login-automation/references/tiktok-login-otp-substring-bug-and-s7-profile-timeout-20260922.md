# TikTok Login: Bẫy Trùng Substring OTP vs Password & Fix Timeout Profile Trên Samsung S7 (2026-09-22)

## 1. Bẫy Trùng Khớp Substring: `'nhap ma'` ↔ `'nhap mat khau'`

### Hiện tượng & Root Cause:
Trong `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py`:
- Danh sách `OTP_HINTS` chứa chuỗi `"nhap ma"`.
- Khi người dùng đăng nhập bằng TikTok ID, TikTok mở màn hình **"Nhập mật khẩu"**.
- Sau khi chuẩn hóa qua `strip_accents(xml).lower()`, chuỗi trên UI trở thành `"nhap mat khau"`.
- Vì `"nhap ma"` là prefix substring của `"nhap mat khau"` (`"nhap ma" + "t khau"`), câu lệnh:
  ```python
  if any(h in flat for h in OTP_HINTS):
  ```
  lập tức đánh giá là `True`.
- Hậu quả: Script nhận diện nhầm màn hình điền Password thành màn hình đòi mã OTP Email, bỏ qua ô mật khẩu và fallback mở ứng dụng Outlook / Gmail trên máy rồi dừng với lỗi `OUTLOOK_APP_INBOX_NOT_VERIFIED`.

### Giải Pháp Chuẩn:
1. **Thêm khoảng trắng ranh giới từ vào `OTP_HINTS`:**
   Đổi `"nhap ma"` thành `"nhap ma "` (có dấu cách phía sau) hoặc dùng `"nhap ma xac minh"` để không bao giờ match với `"nhap mat khau"`.
2. **Đảo thứ tự ưu tiên trong `drive_login_screens`:**
   Luôn đưa nhánh kiểm tra `PASSWORD_HINTS` lên TRƯỚC `OTP_HINTS`. Khi màn hình đang có ô mật khẩu, script phải ưu tiên điền mật khẩu trước. Chỉ khi nào màn hình thực sự hỏi OTP thì mới nhảy sang đọc hòm thư.

```python
# CHUẨN:
if any(h in flat for h in PASSWORD_HINTS):
    fill_password_and_login(device_id, account["tiktok_pass"], stt=stt)
    time.sleep(D_LONG)
    continue

if any(h in flat for h in OTP_HINTS):
    # xử lý email otp
    ...
```

---

## 2. Nâng Trần Timeout Load Profile Cho Thiết Bị Cũ (Samsung S7 / Android 7)

### Hiện tượng:
- Samsung Galaxy S7 (SM-G930F/S) trên nền Android 7/8 phản hồi rất chậm khi chuyển từ For-You feed sang tab Hồ sơ (Profile).
- Hàm `_wait_profile_screen_ready(device_id, timeout=12)` mặc định chỉ đợi 12 giây, và fallback chỉ 6 giây.
- Profile chưa kịp render xong thì timeout đã hết, khiến script tưởng lầm chưa vào được Profile và thực hiện chu kỳ cuộn 400px thử lại nhiều lần dẫn đến fail `Khong mo duoc account dropdown`.

### Giải Pháp Chuẩn:
- Trong `social_reg_v1.py`:
  - Nâng timeout mặc định của `_wait_profile_screen_ready` từ `12` lên `25`.
  - Nâng timeout fallback khi mở dropdown từ `6` lên `20`.
- Đảm bảo app có đủ thời gian tải dữ liệu profile trước khi thực hiện tap mở Switcher.
