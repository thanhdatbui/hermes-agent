# Hotmail API Purchase & ATX XML-First Batch Loading (2026-08-22 / 2026-08-23)

## 1. BoxTaiKhoan API Purchase Integration
- **Endpoint**: `https://boxtaikhoan.com/ajaxs/client/product.php`
- **Action**: `buyProduct`
- **Payload**:
  ```python
  data = {
      "action": "buyProduct",
      "id": "60",  # Gói 60: Hotmail OAuth2 (393đ)
      "amount": amount,
      "api_key": api_key,
      "user_input": "{}"
  }
  ```
- **Format trả về**: `mail|pass|refresh_token|client_id` (được lưu trực tiếp vào `D:\Taadaa\Hotmail\hotmail_input.txt`).

## 2. Pre-Login OAuth2 Token Validation Gate & Corrupted Token Diagnosis
- Khi mua tài khoản từ shop, có thể có token lỗi (HTTP 400 Bad Request khi refresh).
- **BẮT BUỘC** kiểm thử toàn bộ Refresh Token qua Microsoft OAuth2 endpoint trước khi nạp:
  ```python
  url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
  data = f"client_id={cid}&grant_type=refresh_token&refresh_token={urllib.parse.quote(token)}&scope=offline_access%20https://graph.microsoft.com/Mail.Read".encode("utf-8")
  ```
- **Dấu hiệu nhận diện Token bị lỗi/cắt cụt từ kho của shop**:
  - Token hợp lệ thường dài **481 - 501 ký tự** và luôn kết thúc bằng dấu `$`.
  - Token bị cắt cụt thường ngắn (~333 ký tự) và kết thúc lửng. Khi gọi Microsoft trả về: `AADSTS70000: The provided value for the input parameter 'refresh_token' or 'assertion' is not valid` (`invalid_grant`, error code `70000`).
  - Do Client ID ở cuối vẫn đủ 36 ký tự UUID nên chứng minh lỗi do DB shop bị cắt token từ trước chứ không phải do API truyền thiếu.
- Khi gặp token lỗi: Tự động mua bù ngay tài khoản thay thế để batch không bị ngắt quãng, đồng thời xuất mã đơn (`trans_id`) + full info tài khoản lỗi cho user để gửi bảo hành shop.

## 3. Farm Device Eligibility Preflight (VPN & Proxy Check)
- Quét danh sách máy mục tiêu (chưa có Hotmail trong `gmail_clean_v2.xlsx`).
- **Fail-Closed Guard**: Kiểm tra kết nối mạng qua `tun0` và broadcast `ViChanger GET_IP` (retry tối đa 3 lần).
  ```bash
  am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller
  ```
- Chỉ nạp cho các máy có `tun0` UP và trả về IP thật hợp lệ. Loại trừ các máy mất proxy hoặc chưa gán.

## 4. Khắc phục triệt để lỗi xoay ngang màn hình (Rotation Lock Pitfall)
- **Vấn đề**: Khi mở Outlook / Gmail / WebView, Samsung Galaxy S7 tự kích hoạt cảm biến xoay ngang nếu thiếu lệnh khóa hệ thống.
- **Giải pháp**: Phải chạy đầy đủ 4 lệnh:
  ```bash
  settings put system accelerometer_rotation 0
  settings put system user_rotation 0
  content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
  content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
  ```

## 5. Quy trình ATX-Agent XML-First Login (Port 7912)
- **Cấm hoàn toàn tap mù / hardcode tọa độ**.
- **Luồng xử lý**:
  1. Force portrait + khởi động Outlook qua launcher monkey.
  2. Xử lý màn hình onboarding `btn_primary_button` ("THÊM TÀI KHOẢN").
  3. Mở ngăn kéo (`drawer_layout`) -> `btn_add_account` -> `add_normal_account` nếu app đã có sẵn tài khoản.
  4. Chọn loại tài khoản `btn_add_account_outlook` ("Chọn loại tài khoản" -> Outlook).
  5. Điền email vào `auto_complete_input_email` -> Bấm `btn_primary_button` ("TIẾP TỤC").
  6. Điền password vào trường `EditText` / `password=true` -> Bấm "Tiếp theo".
  7. Bấm "Có" ở màn hình "Duy trì đăng nhập?".
  8. Bỏ qua các màn phụ ("Thêm tài khoản khác", "Ghi chú").
  9. Kiểm tra hiển thị tài khoản trong Inbox/Drawer trước khi ghi nhận thành công.

Script chuẩn: `D:\Taadaa\Hotmail\scripts\run_batch_login_xml.py`.
Sau khi nạp thành công, đồng bộ ngày nạp (`YYYY-MM-DD`) vào Cột 7 `gmail_clean_v2.xlsx` và giải phóng device lock.
