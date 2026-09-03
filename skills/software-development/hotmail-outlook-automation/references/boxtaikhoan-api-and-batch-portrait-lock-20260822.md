# Boxtaikhoan API & Portrait Guard Invariants (2026-08-22)

## 1. Mua tài khoản tự động qua API `boxtaikhoan.com`
- **Endpoint**: `https://boxtaikhoan.com/ajaxs/client/product.php`
- **Payload**:
  - `action`: `buyProduct`
  - `id`: ID gói sản phẩm (ví dụ: `60` cho Hotmail OAuth2 393đ)
  - `amount`: số lượng cần mua
  - `api_key`: API key tài khoản
- **Kết quả trả về**:
  - Trả về JSON chứa chuỗi accounts (`mail|pass|refresh_token|client_id`).
  - Ghi vào file `hotmail_input.txt` trong repo `Hotmail`.

## 2. Hard Portrait Lock (Chống tự xoay màn hình Android/Samsung)
- **Vấn đề**: Cài đặt `accelerometer_rotation=0` và `user_rotation=0` không đủ ngăn ứng dụng (Outlook/Chrome) tự xoay sang Landscape khi khởi chạy trên Android 8 / Samsung S7.
- **Giải pháp bắt buộc**:
  ```bash
  adb -s <serial> shell "settings put system accelerometer_rotation 0 && settings put system user_rotation 0 && wm user-rotation lock 0"
  ```
- **Quy tắc Batch**: Mọi runner / batch script bắt buộc gọi `wm user-rotation lock 0` trước khi mở app.
