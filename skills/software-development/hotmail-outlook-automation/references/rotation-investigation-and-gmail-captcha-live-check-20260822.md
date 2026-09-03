# Investigation: Android Screen Rotation & Live Gmail Captcha Verification (2026-08-22)

## 1. Root Cause Analysis: Unintended Screen Rotation on Samsung Devices

### Triệu chứng:
Máy Samsung (ví dụ Máy 69) liên tục bị xoay ngang màn hình (`mCurrentRotation = 1` hoặc `mDesiredRotation = 1`), khiến tọa độ tap bị lệch, UI XML dump bị đảo chiều `width > height`, làm fail các flow Login Outlook hoặc TikTok Password Change.

### Nguyên nhân kỹ thuật:
- Các script chuẩn bị máy (`prepare_device` hoặc `run_batch_login_locked.py`) thường chỉ thực hiện ghi setting:
  ```bash
  settings put system accelerometer_rotation 0
  settings put system user_rotation 0
  ```
- Tuy nhiên, trên ROM Samsung Android 8/9, khi một ứng dụng khởi chạy với Activity có config đa hướng (`configChanges="orientation"` hoặc WebView form), hệ thống WindowManager vẫn có thể tự động chuyển sang Landscape nếu chưa có lệnh khóa cứng cấp độ WindowManager.

### Giải pháp bắt buộc:
Sau khi ghi `settings`, BẮT BUỘC phải thực hiện lệnh khóa xoay dọc của WindowManager:
```bash
wm user-rotation lock 0
```
Và kiểm tra lại trạng thái:
```bash
adb shell dumpsys window | grep mCurrentRotation
# Kết quả phải trả về 0 (Portrait)
```

---

## 2. Quy trình Kích hoạt Module Check Live Gmail trên Máy Thật khi Bị Lỗi Sync

### Triệu chứng:
Tài khoản Gmail trên máy báo lỗi `Sync failed` trong `Cài đặt -> Tài khoản -> Google -> Đồng bộ tài khoản`, không tải được thư mới chứa OTP TikTok.

### Quy trình kích hoạt xác minh Live:
1. Kéo thanh thông báo hệ thống (Notification shade) xuống.
2. Tìm thông báo từ `Dịch vụ Google Play` có nội dung *"Yêu cầu đăng nhập - Đăng nhập để tiếp tục sử dụng <email>"*.
3. Bấm trực tiếp vào thông báo để mở luồng xác thực Google Play Services.
4. Bấm `TIẾP THEO` trên màn hình *"Xác minh danh tính của bạn"*.
5. Phân loại kết quả:
   - **Màn hình hiện:** *"Xác minh danh tính của bạn - Xác nhận bạn không phải là rô-bốt (Captcha Bot)"* -> Tài khoản đã bị Google chặn bot / checkpoint.
   - **Xử lý theo quy định Farm:** Phân loại tài khoản là DIE / CAPTCHA BOT -> Gọi quy trình Cleanup: xóa tài khoản khỏi máy và cập nhật xóa dữ liệu tương ứng trong Excel.
