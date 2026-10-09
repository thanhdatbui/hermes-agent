# Hotmail Recovery & TikTok Password Reset Flow for Phone Farm (2026-09-18)

## 1. Hotmail Login & Recovery on Android S7
- **Outlook App Redirect Trap:**
  - Trên các máy Samsung S7 (Android 8), WebView trong ứng dụng Outlook (`com.microsoft.office.outlook`) thường tự động redirect các tài khoản Hotmail cũ/lạ sang màn hình `Tạo tài khoản Microsoft mới (@outlook.com.vn)`. Không xuất hiện ô nhập password hay link nhận OTP khôi phục.
  - **Khắc phục chuẩn (Canonical):** Dùng trình duyệt Chrome (`com.android.chrome`) theo luồng `login_web_legacy`.
- **Vượt chốt chặn bảo mật Microsoft bằng `thanhdatbui1995@gmail.com`:**
  - Khi Microsoft báo sai pass hoặc kích hoạt xác minh: Chọn link `Gửi mã đến th*****@gmail.com`.
  - Nhập email khôi phục `thanhdatbui1995@gmail.com`.
  - Dùng script kết nối IMAP (`imap.gmail.com:993`) qua `flows/hotmail_recovery.py` (sử dụng biến môi trường `OTP_MAIL_USER` và `OTP_MAIL_APP_PASSWORD`) để tự động đọc mã OTP 6 số.
  - Điền OTP ➔ Nhấn Back khi hiện popup passkey ➔ Chọn `Có` ở màn hình Duy trì đăng nhập ➔ Vào thẳng Inbox `outlook.live.com/mail/0/inbox`.

## 2. TikTok Reset Password Workflow (Gỡ kẹt nick chưa có mật khẩu thật)
- **Bản chất lỗi:**
  - Các tài khoản phôi reg đợt cũ thường qua bước OTP email là vào thẳng profile, chưa từng nhập mật khẩu trên TikTok.
  - Lúc này, nếu App TikTok trên máy mới bắt `Xác minh danh tính: Nhập mật khẩu`, không thể dùng pass cũ trong Excel (vì pass đó là pass ảo bị bug fallback tự sinh).
  - Trên App TikTok, bấm "Đặt lại mật khẩu bằng email" sẽ bị server đá văng về màn hình đăng nhập ban đầu hoặc FAQ hỗ trợ vì thiết bị mới chưa đủ điểm tin cậy.
- **Quy trình Reset chuẩn (Gỡ kẹt qua Web/Chrome):**
  1. Mở trang reset mật khẩu TikTok trên Chrome (`https://www.tiktok.com/login/email/forget-password` hoặc qua thẻ ẩn danh).
  2. Điền email Hotmail ➔ Bấm Gửi mã.
  3. Lấy mã xác minh 6 số từ hộp thư Hotmail (qua Graph API nếu có Token, hoặc qua tab Inbox Chrome đang mở).
  4. Tạo mật khẩu mới: **TUYỆT ĐỐI KHÔNG DÙNG ĐUÔI `@Ks`**. Bắt buộc dùng `core.passwords.generate_account_password(16-18)` sinh pass mạnh gồm chữ hoa, chữ thường, số, dấu gạch nối (vd: `ccOplL2wL-eg-OkD`).
  5. Sau khi đổi pass thành công trên web ➔ Mở App TikTok ➔ Nhập email + OTP + mật khẩu mới vừa tạo ➔ Đăng nhập thành công vào app.
  6. Đồng bộ ngay mật khẩu mới vào đồng loạt các workbook liên quan (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `TikN.xlsx`).
