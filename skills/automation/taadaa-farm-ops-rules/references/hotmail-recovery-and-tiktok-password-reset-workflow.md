# Quy trình Giải cứu & Chuẩn hóa Tài khoản Hotmail / TikTok Farm

## 1. Bản chất sự cố lệch Pass trên Phone Farm
1. **Reg không có pass thật:** Luồng đăng ký TikTok bằng Email (Hotmail/Gmail) thường cho vào thẳng trang cá nhân (Profile) mà không yêu cầu tạo mật khẩu.
2. **Bug ghi pass ảo:** Script reg cũ có fallback `make_tiktok_password(mail_pw)` tự bịa chuỗi pass ngẫu nhiên ghi vào Excel trong khi server TikTok chưa từng được đặt mật khẩu đó.
3. **Cấm pass @Ks:** User đã cấm vĩnh viễn quy ước mật khẩu cũ có đuôi `@Ks` (ví dụ `Ten@Ks` hay `Susan123@Ks`). Phải dùng hàm `generate_account_password()` (chuỗi ngẫu nhiên 18 ký tự mạnh) khi đặt hoặc xoay tua mật khẩu.

## 2. Giải cứu Hotmail qua Email Khôi phục (`thanhdatbui1995@gmail.com`)
Khi đăng nhập Hotmail trên thiết bị Android mới (Samsung Galaxy S7) bị báo sai mật khẩu hoặc kích hoạt chốt chặn bảo mật Microsoft:
- **Cảnh báo App Outlook:** App Outlook Android thường tự động chuyển hướng sai sang màn hình *Tạo tài khoản Microsoft mới (@outlook.com.vn)*.
- **Giải pháp:** Bắt buộc dùng trình duyệt **Chrome Android** (`login.live.com` qua `login_web_legacy`).
- **Quy trình bắt OTP khôi phục:**
  1. Bấm vào liên kết: `Gửi mã đến th*****@gmail.com`.
  2. Điền email khôi phục: `thanhdatbui1995@gmail.com` ➔ Bấm Gửi mã.
  3. Dùng IMAP SSL (`imap.gmail.com:993`) đọc OTP 6 số từ mailbox `thanhdatbui1995@gmail.com` (cấu hình qua `OTP_MAIL_USER` và `OTP_MAIL_APP_PASSWORD`).
  4. Điền mã OTP vào trang Microsoft, bấm `Back` một lần nếu xuất hiện hộp thoại Passkey của Google Play Services, sau đó bấm `Có` (tâm bounds `[72,1572][1008,1686]` -> `(540, 1629)`) để duy trì đăng nhập vào Inbox (`outlook.live.com/mail/0/inbox`).

## 3. Khôi phục / Đặt lại Mật khẩu TikTok qua Web Chrome
Khi app TikTok đòi mật khẩu mà tài khoản chưa có mật khẩu thật hoặc mật khẩu trong Excel bị lệch:
1. Mở Chrome đến trang: `https://www.tiktok.com/login/phone-or-email/email`.
2. Bấm `Bạn quên mật khẩu?` ➔ Chọn `Email`.
3. Nhập địa chỉ Hotmail của tài khoản ➔ Bấm `Gửi mã`.
4. Mở tab Outlook Inbox trên Chrome (`outlook.live.com/mail/0/inbox`), vuốt refresh lấy mã OTP 6 số từ TikTok gửi về.
5. Nhập mã OTP vào trang Reset mật khẩu của TikTok.
6. Đặt mật khẩu mới theo chuẩn an toàn (18 ký tự, không dùng `@Ks`).
7. Đăng nhập vào app TikTok bằng Email + OTP + Mật khẩu mới vừa đặt.
8. Cập nhật đồng loạt mật khẩu mới vào các file Excel dữ liệu (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `TikN.xlsx`).
