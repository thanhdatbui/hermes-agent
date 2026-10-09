# Hotmail Replacement & TikTok Relink on Missing Web Password (2026-10-01)

## 1. Bối cảnh & Hiện tượng thực tế

- **Hiện tượng**:
  - Tài khoản Hotmail cổ trên farm (như `yobifqtxkbhpzmxf@hotmail.com` trên Máy 34) bị trống trường `PASS MAIL` trong Master Excel `taikhoan_dat_v2_updated .xlsx`.
  - Supervisor GPM (`batch_gpm_5profiles_supervisor.py`) tự động lấy nhầm mật khẩu TikTok (`info.get("password")`) để thử login vào Microsoft Webmail (`login.live.com`), dẫn đến lỗi sai mật khẩu liên tục và bị khóa sang trạng thái `BLOCKED`.
  - User thắc mắc tại sao mail không có pass và yêu cầu vào BoxTaiKhoan kiểm tra.

---

## 2. Bản chất kỹ thuật & Cơ chế đối soát

### 2.1. Tại sao tài khoản mất Pass Web nhưng vẫn có TikTok sống?
1. **Cơ chế Android IMAP App**:
   - Trên điện thoại thật (Samsung Galaxy S7), luồng đăng ký TikTok đọc OTP trực tiếp từ giao diện ứng dụng Gmail Android (`com.google.android.gm.legacyimap`) qua ADB / UI dump.
   - Khi mail đã được add sẵn trong máy từ nhiều tháng trước, tool reg TikTok mở app đọc mã OTP tạo tài khoản thành công mà **không cần biết mật khẩu web của Hotmail**.
   - Khi lưu vào Excel, tool chỉ ghi nhận mật khẩu TikTok (`PASS`) và bỏ trống cột `PASS MAIL` (`None`).
2. **Cơ chế GPM Supervisor trên PC**:
   - Để đăng ký ChatGPT / Codex, PC bắt buộc phải mở browser đăng nhập webmail Microsoft qua proxy để nhận thư hoặc cấp token.
   - Trống `PASS MAIL` khiến script fallback nhầm pass TikTok và thất bại.

### 2.2. Kiểm tra BoxTaiKhoan API
- Endpoint profile & số dư:
  `GET https://boxtaikhoan.com/api/profile.php?api_key=<API_KEY>`
  Headers: `User-Agent: Mozilla/5.0`
- API của BoxTaiKhoan không hỗ trợ endpoint tra cứu lịch sử đơn hàng dạng REST public (`/api/orders.php` hay `/api/history.php` đều trả về HTTP 404).
- Các đơn hàng mua ngoài chỉ lưu tạm trong `state.db` của Hermes hoặc các file `.txt` nguồn (`latest_bought_*.txt`, `hotmail_all_60_bought.txt`).
- Các tài khoản tạo từ tháng 06/2026 trở về trước hoàn toàn không nằm trong lịch sử đơn mua BoxTaiKhoan tháng 08/2026.

---

## 3. Quy trình chuẩn hóa Thay thế Mail & Đổi liên kết TikTok

### Bước 1: Trích xuất Hotmail mới từ kho nội bộ
- Quét các nguồn mail dự phòng chưa qua sử dụng:
  + `D:\Taadaa\Hotmail\hotmail_input.txt` (Ưu tiên số 1 - có sẵn Graph OAuth2 Refresh Token).
  + `D:\Taadaa\Hotmail\latest_bought_70.txt`.
  + `D:\OneDrive\hotmainew.txt`.
- Đối soát loại trừ các email đã xuất hiện trong `taikhoan_dat_v2_updated .xlsx` hoặc `batch_gpm_5profiles_supervisor_state.json`.
- Kiểm tra liveness của Refresh Token qua Microsoft OAuth2 endpoint (`scope="offline_access https://graph.microsoft.com/Mail.ReadWrite"`), đảm bảo trả về HTTP 200 và có `access_token`.

### Bước 2: Đồng bộ 3 điểm dữ liệu (Excel + Supervisor State + Input Text)
1. **Master Excel (`taikhoan_dat_v2_updated .xlsx`)**:
   - Tạo bản backup: `taikhoan_dat_v2_updated_before_replace_<tag>_<timestamp>.xlsx`.
   - Cập nhật Cột F (Email) = Email mới.
   - Cột G (`PASS MAIL`) = Pass mail mới.
   - Cột L (`PASS CHATGPT`) = Pass mail mới (nếu chưa có pass ChatGPT riêng).
2. **GPM Supervisor State (`batch_gpm_5profiles_supervisor_state.json`)**:
   - Tạo bản backup: `batch_gpm_5profiles_supervisor_state_before_replace_<tag>_<timestamp>.json`.
   - Xóa key cũ `M<machine>:<old_email>`, tạo key mới `M<machine>:<new_email>`.
   - Gán `stage = "HOTMAIL_LOGIN"` (hoặc `"CHATGPT_REG"` nếu có token Graph API), `status = "PENDING"`, xóa sạch `error` và `last_result`.
3. **Hotmail Input File (`D:\Taadaa\Hotmail\hotmail_input.txt`)**:
   - Xóa dòng mail vừa sử dụng để tránh bị cấp trùng cho profile khác.

### Bước 3: Đổi Email liên kết trên TikTok App qua 2FA TOTP
1. Mở TikTok trên máy Android, chuyển sang đúng nick cần đổi email.
2. Vào **Cài đặt và quyền riêng tư** $\rightarrow$ **Tài khoản** $\rightarrow$ **Thông tin người dùng** $\rightarrow$ **Email** $\rightarrow$ **Thay đổi email**.
3. **Vượt Gate Xác minh Danh tính bằng TOTP**:
   - Không chọn gửi OTP về mail cũ (vì mail cũ không có pass hoặc không vào được).
   - Chọn phương thức xác thực bằng **Mã xác thực 2FA (Authenticator)**.
   - Lấy `secret_2fa` từ Cột E trong Excel, sinh mã 6 số:
     ```python
     import pyotp
     otp = pyotp.TOTP(secret_2fa.strip()).now()
     ```
   - Nhập OTP vào form để vượt qua bước xác nhận danh tính thành công.
4. **Nhập Hotmail mới & Bốc OTP Graph API**:
   - Nhập Hotmail mới $\rightarrow$ Bấm Gửi mã.
   - Gọi Microsoft Graph API lấy OTP 6 số từ OpenAI / TikTok gửi về hộp thư.
   - Nhập mã vào TikTok và hoàn tất.
