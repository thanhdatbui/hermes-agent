# ChatGPT GPM Dual-Channel OTP Retrieval, Lifecycle Caching & Safe Purge

## 1. Dual-Channel OTP Retrieval (Graph API -> Canonical Webmail Fallback)
Khi tự động re-login tài khoản ChatGPT trên trình duyệt GPM gặp màn hình yêu cầu mã OTP 6 số:

### Kênh 1: Microsoft Graph API (Ưu tiên, O(1) < 2s)
- **Điều kiện**: Tài khoản Hotmail còn OAuth `refresh_token` và `client_id` hợp lệ.
- **Scope**: `https://graph.microsoft.com/Mail.Read offline_access`.
- **Thực hiện**: Gọi endpoint lấy bearer token -> đọc thư mới nhất từ OpenAI -> parse regex `\b(\d{6})\b`.
- **Thất bại**: Nếu token hết hạn (HTTP 400 `invalid_grant`) hoặc không có token trong kho mua -> tự động chuyển ngay sang Kênh 2.

### Kênh 2: Webmail Outlook Fallback trên GPM (Dùng code login canonical có sẵn)
- **Nguyên tắc bất biến**: CẤM tự chế selector mới hoặc viết script đăng nhập mò mẫm. Bắt buộc dùng lại logic và selector chuẩn từ `batch_gpm_hotmail_password_login.py` và `read_otp_gpm.py`:
  1. Mở tab mới qua CDP: `http://{host_port}/json/new?https://outlook.live.com/mail/0/`.
  2. Kiểm tra nếu URL chuyển hướng về `login.live.com` hoặc `login.microsoftonline.com`:
     - Điền email vào `input[name="loginfmt"]` / `input[type="email"]` -> bấm nút submit `#idSIButton9`.
     - Bắt và click bypass nút đổi phương thức mật khẩu: `#idA_PWD_SwitchToPassword` ("Sử dụng mật khẩu của bạn / Use your password instead").
     - Điền mật khẩu từ kho dữ liệu (Excel/file mua) vào `input[name="passwd"]` -> submit `#idSIButton9`.
     - Vượt màn hình duy trì đăng nhập (KMSI): click `#declineButton` hoặc `#idSIButton9`.
  3. Quét danh sách email (`[role="row"]` hoặc `document.body.innerText`) tìm thư từ OpenAI để bóc mã OTP 6 chữ số.
  4. Đóng tab webmail sau khi lấy mã để giải phóng RAM cho GPM profile.

---

## 2. Vòng đời Tài khoản ChatGPT & O(1) Skip cho Nick Die (`account_deactivated`)

### Cơ chế nhận diện & Cache trạng thái
- **Dấu hiệu die vĩnh viễn**: Màn hình lỗi xác thực OpenAI chứa text `"Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa"`, mã lỗi `error_code: account_deactivated`.
- **Lưu state O(1) Skip**:
  - Ghi nhận vào file trạng thái tập trung: `D:/Taadaa/runtime/chatgpt_account_lifecycle.json`:
    ```json
    {
      "user@hotmail.com": {
        "status": "DEAD_DEACTIVATED",
        "updated_at": 1728654321.0,
        "proof": "D:/Taadaa/runtime/artifacts/deactivated_user.png"
      }
    }
    ```
  - Chụp ảnh màn hình lưu bằng chứng artifacts trước khi đóng browser.
  - **O(1) Skip Invariant**: Mọi lần quét sau (chạy tay hoặc Cron) kiểm tra file state đầu tiên. Nếu `status == "DEAD_DEACTIVATED"`, **bỏ qua ngay lập tức (< 0.5s)** mà không khởi động profile GPM.

### Cơ chế Purge an toàn (Chống xóa nhầm)
- Khi purge tài khoản die khỏi OmniRoute (`~/.omniroute/storage.sqlite`) và 9Router:
  - **CẤM so sánh substring lỏng lẻo** (`email in name` / `email in row`): Dễ xóa nhầm các tài khoản có domain hoặc tiền tố tương tự (ví dụ: `user@domain.com` xóa nhầm `user@domain.com.vn`).
  - **Bắt buộc hàm so sánh chính xác (`is_account_match`)**:
    - Khớp chính xác email (`target == row_email.strip()`).
    - Hoặc khớp tên có ranh giới rõ ràng (`name.startswith(target + " ")` hoặc `name.startswith(target + "(")`).
  - Xóa ID khỏi bảng `provider_connections`.
  - Làm sạch ID khỏi danh sách `models` trong bảng `combos` (cột `data` JSON).
  - Đồng bộ qua API `DELETE /api/providers/{id}` và `PUT /api/combos/{id}` của OmniRoute & 9Router.

---

## 3. Re-OAuth & Cập nhật Session Token khi Acc Sống (LIVE)
- Khi tài khoản đăng nhập thành công vào giao diện ChatGPT (`chatgpt.com`):
  - Dùng CDP gọi lệnh `Network.getCookies` với URL `https://chatgpt.com`.
  - Trích xuất cookie `__Secure-next-auth.session-token`.
  - Cập nhật session token mới vào `provider_connections` (cột `config` JSON chứa `session_token` / `sessionToken`).
  - Cập nhật state `"status": "LIVE"`, `"has_token": true`.
  - Reload combo reviewer (`review`, `chatgpt-web-pool`, `gpt-web-sol`) để đưa tài khoản trở lại pool hoạt động.
