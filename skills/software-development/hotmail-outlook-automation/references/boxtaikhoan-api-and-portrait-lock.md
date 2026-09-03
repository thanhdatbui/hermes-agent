# Boxtaikhoan API & Force Portrait Protocols

## 1. Mua Hotmail tự động qua Boxtaikhoan API
- Endpoint: `POST https://boxtaikhoan.com/ajaxs/client/product.php`
- Payload Form-Data:
  ```python
  data = {
      "action": "buyProduct",
      "api_key": API_KEY,
      "product_id": 60, # Hotmail OAuth2 (393đ)
      "amount": quantity,
      "coupon": ""
  }
  ```
- Format tài khoản trả về trong `res["data"]["accounts"]`:
  `mail|pass|refresh_token|client_id` (mỗi dòng 1 account).
- Lưu ngay vào `D:\Taadaa\Hotmail\hotmail_input.txt`.

## 2. Chuẩn hóa Khóa xoay dọc (Force Portrait Lock) chống xoay ngang trên Samsung S7
Trên Samsung S7 / Android 7.0+, lệnh `wm user-rotation` có thể báo lỗi `unknown command`. Để khóa cứng 100% hướng dọc (`mCurrentRotation=0`), chạy đồng thời:
```bash
settings put system accelerometer_rotation 0
settings put system user_rotation 0
content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
```
Kiểm tra lại qua:
```bash
dumpsys window | grep -E "mCurrentRotation|mUserRotation"
```
Đảm bảo `mCurrentRotation=0` trước khi mở Outlook / TikTok / Settings.

## 3. Quy trình thay Email TikTok khi Gmail cũ bị Captcha/Die
- Khi Gmail cũ bị Google khóa ("Xác nhận bạn không phải là rô-bốt") -> Xóa Google account khỏi máy và `gmail_clean_v2.xlsx`.
- Để gán Hotmail mới vào nick TikTok đang active trên máy mà không bị kẹt màn hình OTP của Gmail cũ:
  1. Mở TikTok -> Hồ sơ (Profile) -> Menu 3 gạch -> `Cài đặt và quyền riêng tư`.
  2. Chọn `Tài khoản` -> `Thông tin tài khoản` -> `Email`.
  3. Chọn `Thay đổi email` -> Nhập Hotmail mới -> Bấm `Tiếp tục`.
  4. Đọc OTP gửi về Hotmail mới qua OAuth2 Refresh Token (Graph API / Outlook API) để hoàn tất.
