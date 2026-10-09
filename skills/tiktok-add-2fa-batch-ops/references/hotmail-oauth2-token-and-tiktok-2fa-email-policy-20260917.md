# Hotmail/Outlook OAuth2 Token Retrieval & TikTok 2FA Email Policy (17/09/2026)

## 1. Cơ Chế TikTok Chặn Tắt 2FA Email Trên Tài Khoản No-Phone
- **Hiện tượng:** Khi tài khoản TikTok đã bật `Trình xác thực: Bật` (TOTP) và `Mật khẩu: Bật`, thực hiện tap `Email` -> `Xóa` -> `Xác nhận` trên dialog "Xóa email?":
  - TikTok hiển thị Toast: `"Không thể thay đổi cài đặt vì lý do bảo mật, hãy thử lại sau"` (Toast đen).
  - Dòng `Email` vẫn giữ trạng thái `Bật`. Runner văng lỗi `EMAIL_DISABLE_NOT_STABLE`.
- **Bản chất nghiệp vụ & Vận hành:**
  - TikTok áp đặt Security Cooldown trên tài khoản mới reg / đổi pass hoặc chưa liên kết Số điện thoại (no-phone).
  - **Quy tắc:** Không cố ép tắt 2FA Email trên TikTok. Tài khoản sau khi bật Trình xác thực (TOTP) + Mật khẩu mạnh đã đủ an toàn để đăng nhập máy khác/tool bằng TOTP mà không bị gửi OTP mail.
  - Sau này khi giao tài khoản cho khách vẫn bàn giao trọn bộ kèm mail gốc (TikTok + Hotmail), nên việc giữ liên kết email là hoàn toàn tự nhiên và cần thiết.

## 2. Rủi Ro Bên Bán Back Mail & Giải Pháp Đổi Pass Hotmail Sớm
- **Vấn đề:** Để bên bán Hotmail giữ mật khẩu gốc lâu ngày có nguy cơ bị back tài khoản TikTok (thông qua khôi phục mật khẩu hoặc đọc OTP nếu chưa có TOTP).
- **Giải pháp triệt để:** 
  - Đổi mật khẩu Hotmail sớm bằng flow có sẵn (`flows/hotmail_change_info.py` / `task_change_password`) và cập nhật cột G (`PASS MAIL`) Excel.
  - Khi đổi pass Hotmail, Microsoft tự động **revoke (hủy hiệu lực) toàn bộ `refresh_token` cũ của bên bán**. Bên bán mất quyền truy cập vĩnh viễn.

## 3. Pitfalls Khi Tự Động Hóa Lấy Refresh Token Qua Trình Duyệt Trên Android
- **Lỗi ngắt lệnh ADB do ký tự `&` trong URL (AADSTS900144):**
  - Khi mở Chrome qua lệnh `am start -a android.intent.action.VIEW -d "<URL>"`, các ký tự `&` trong URL OAuth (như `&scope=...`, `&prompt=...`) bị shell Linux cắt làm lệnh chạy ngầm.
  - Microsoft chỉ nhận được URL cụt và trả về lỗi: `AADSTS900144: The request body must contain the following parameter: 'scope'`.
  - **Khắc phục:** Luôn escape ký tự `&` thành `\&` hoặc bọc URL trong dấu nháy kép/đơn khi truyền qua ADB shell.
- **Hiện tượng Chrome cắt bớt URL redirect (Ellipsis truncation):**
  - Khi Microsoft redirect về `https://login.microsoftonline.com/common/oauth2/nativeclient?code=M.C...`, thanh địa chỉ `url_bar` trên Android tự động rút gọn và hiển thị dấu `...`, khiến việc đọc qua Accessibility XML / UI dump bị mất đoạn đuôi của `code` -> Gửi POST đổi token báo lỗi `malformed code` (AADSTS9002313).
  - Để lấy full redirect URL cần dùng Chrome remote devtools socket hoặc xử lý copy clipboard, hoặc ưu tiên dùng Outlook App trên máy để đọc OTP trực tiếp mà không cần phụ thuộc OAuth Graph API.
