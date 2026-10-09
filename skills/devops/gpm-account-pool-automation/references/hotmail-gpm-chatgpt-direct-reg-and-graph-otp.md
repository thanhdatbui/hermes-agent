# Hotmail GPM Direct ChatGPT Registration & Microsoft Graph OTP

## 1. Kiến trúc luồng đăng ký ChatGPT bằng Hotmail trên GPM
- **Khác biệt với Gmail**:
  - Không mở tab phụ trên trình duyệt để đọc mail (tránh làm phân tán Playwright CDP và tránh popup cookie Outlook).
  - Sử dụng **Microsoft Graph API** (`https://graph.microsoft.com/v1.0/me/messages`) qua OAuth `refresh_token` và `client_id` (được lưu tại `D:\Taadaa\Hotmail\hotmail_input.txt` hoặc workbook nguồn).
  - Tự động lấy `access_token` bằng scope `https://graph.microsoft.com/Mail.Read offline_access` với fallback `ALT_CLIENT_IDS` (Outlook Mobile `27922004-5251-4030-b22d-91ecd9a37ea4`, Office `d3590ed6...`, Azure CLI `1b730954...`).
- **Chính sách mật khẩu (PASS CHATGPT)**:
  - Mật khẩu tạo tài khoản ChatGPT được giải quyết độc lập từ cột `PASS CHATGPT` (Cột L / Index 11) trong `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`.
  - Mật khẩu đăng nhập Hotmail (`PASS MAIL`) chỉ dùng để duy trì session Microsoft Account trên GPM.
  - Về sau khi đổi pass Hotmail (sau 7 ngày), mật khẩu Hotmail sẽ được cập nhật đồng bộ về cùng giá trị với `PASS CHATGPT` để thuận tiện quản lý.

## 2. Các cạm bẫy kỹ thuật (Pitfalls & Bắt buộc tuân thủ)

### Bẫy 1: Lệch múi giờ & Clock Skew giữa Graph API và Local Clock
- **Hiện tượng**: OpenAI gửi mail OTP rất nhanh (trong 2-5 giây), nhưng Graph API trả về `receivedDateTime` tính theo giờ server Microsoft (UTC). Nếu máy local so sánh cứng `received_after = datetime.now(timezone.utc)`, do độ lệch clock hoặc network latency, tin nhắn OTP bị bỏ qua và dẫn tới `FAIL_OTP_TIMEOUT`.
- **Giải pháp**: Luôn cấp dung sai tối thiểu 60 giây khi bắt đầu đợi OTP:
  ```python
  otp_started_at = datetime.now(timezone.utc) - timedelta(minutes=1)
  otp_code = graph_provider.fetch_otp(received_after=otp_started_at)
  ```

### Bẫy 2: Khoảng trắng trong tên file Excel nguồn
- File nguồn thực tế là `taikhoan_dat_v2_updated .xlsx` (có dấu cách trước đuôi `.xlsx`).
- Tuyệt đối không hardcode duy nhất một đường dẫn không có dấu cách:
  ```python
  UPDATED_XLSX_CANDIDATES = [
      Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"),
      Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated.xlsx"),
  ]
  UPDATED_XLSX = next((p for p in UPDATED_XLSX_CANDIDATES if p.exists()), UPDATED_XLSX_CANDIDATES[0])
  ```

### Bẫy 3: Phân định luồng Signup của OpenAI
- Khi submit email `@hotmail.com` tại `https://chatgpt.com/auth/login?screen_hint=signup`:
  1. OpenAI có thể chuyển thẳng sang màn hình **OTP Verification** (bỏ qua bước password ban đầu).
  2. Sau khi nhập OTP thành công, OpenAI mới hiển thị form tạo mật khẩu $\rightarrow$ Điền `PASS CHATGPT` (được chuẩn hóa `>= 12 ký tự` qua `normalize_password`).
  3. Tiếp theo là form **About you** (Tên, Tuổi / Ngày sinh) $\rightarrow$ Điền tên ngẫu nhiên hoặc chuẩn farm.
  4. Xác nhận đăng ký thành công bằng sự xuất hiện của giao diện chính ChatGPT composer và nút Account/Profile.
