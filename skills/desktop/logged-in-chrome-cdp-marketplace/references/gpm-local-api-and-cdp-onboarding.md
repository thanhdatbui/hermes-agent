# GPMLogin Local REST API & Chrome CDP Direct Operations Reference

## 1. GPMLogin Local REST API Basics (Default Port: 19995)
- Endpoint port được lưu tại: `%LOCALAPPDATA%/Programs/GPMLogin/api_port.dat` (hoặc fallback `19995`).
- Kiểm tra danh sách profile:
  `GET http://127.0.0.1:19995/api/v3/profiles?page=1&per_page=100`
- Khởi tạo profile mới:
  `POST http://127.0.0.1:19995/api/v3/profiles/create`
  Payload JSON:
  ```json
  {
    "profile_name": "Profile_Name",
    "raw_proxy": "",
    "group_id": 1,
    "browser_type": "Chrome",
    "browser_version": "142.0.7444.163"
  }
  ```
  *(Để trống `raw_proxy` nếu muốn chạy trực tiếp bằng IP gốc của máy).*

- Khởi động profile:
  `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?win_scale=0.8&addination_args=--mute-audio&addition_args=--mute-audio`
  *Lưu ý: Vendor API GPMLogin có lỗi chính tả `addination_args` trong C# backend models, nên truyền cả hai để tương thích.*
  Trả về JSON chứa `remote_debugging_address` (ví dụ `127.0.0.1:56225`).

## 2. Kết nối và Điều khiển Chrome qua CDP WebSocket Native
- Lấy WebSocket Debugger URL của page tab:
  `GET http://{remote_debugging_address}/json/list`
  Tìm phần tử có `"type": "page"` và lấy trường `"webSocketDebuggerUrl"`.
- Dùng thư viện `websockets` (Python) gửi lệnh chuẩn Chrome DevTools Protocol:
  * **Điều hướng:**
    `{"id": 1, "method": "Page.navigate", "params": {"url": "https://..."}}`
  * **Chụp màn hình:**
    `{"id": 2, "method": "Page.captureScreenshot", "params": {"format": "png"}}` -> decode base64 ghi ra file `.png`.
  * **Thực thi JS / Điền form:**
    `{"id": 3, "method": "Runtime.evaluate", "params": {"expression": "(...)()"}}`

## 3. Quy tắc Hợp tác Đăng ký Tài khoản Nhạy Cảm (Co-working Onboarding)
- Khi gặp các luồng cần thẻ Visa/Mastercard (AWS, GCP, Azure, Oracle Cloud):
  1. Agent chủ động chuẩn bị môi trường: mở trình duyệt GPM/Chrome, điều hướng vào trang đích, kiểm tra và gửi ảnh xác nhận (Gate 6).
  2. Bắt đầu từ form thông tin công khai (Email, Account Name): Agent tự động điền và bấm gửi mã xác nhận.
  3. Khi đến bước nhập thẻ/OTP SMS/Voice: Dừng lại bàn giao hoặc phối hợp để User nhập trực tiếp, không bao giờ hỏi lưu credential thô.
