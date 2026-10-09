# Hotmail Recovery via thanhdatbui1995@gmail.com, Password Reset Policy & Cron Safety (2026-09-17/18)

## 1. Mật khẩu TikTok Farm: Tuyệt đối cấm đuôi `@Ks` và cấm tự bịa pass ảo
- **User Rule 2026-08-16 & 2026-09-17:**
  + Khi tài khoản reg không qua bước tạo mật khẩu (email-only/OTP signup): Cột `PASS` trong Excel bắt buộc để trống (`""` / `None`). Tuyệt đối CẤM fallback tự chế mật khẩu bằng `make_tiktok_password(mail_pw)` ghi vào Excel.
  + ĐÃ BỎ HOÀN TOÀN quy ước mật khẩu cũ dạng `Ten@Ks` (ví dụ `Susan123@Ks`).
  + Mọi mật khẩu TikTok mới bắt buộc phải sinh bằng `core.passwords.generate_account_password(16|18)` (chuỗi ngẫu nhiên mạnh gồm chữ hoa, chữ thường, số và ký tự gạch nối `-`).
  + Khi chạy Add 2FA (`tiktok-add-bao-mat-f2a`), hàm `password_needs_rotation` sẽ nhận diện các mật khẩu cũ có dạng `@Ks` hoặc trống để tự động xoay tua sang mật khẩu mạnh chuẩn 18 ký tự mới.

## 2. Khôi phục tài khoản Hotmail qua `thanhdatbui1995@gmail.com`
- **Hiện tượng:**
  + Khi đăng nhập Hotmail trên thiết bị mới, Microsoft có thể báo mật khẩu cũ không đúng do đã chạy luồng đổi pass bảo mật trước đó, hoặc chặn do thiết bị lạ.
  + Màn hình Microsoft xuất hiện liên kết: `Gửi mã đến th*****@gmail.com`.
- **Quy trình tự động hóa:**
  1. Dùng WinRT OCR hoặc tọa độ click vào dòng `Gửi mã đến th*****@gmail.com`.
  2. Điền email khôi phục đầy đủ: `thanhdatbui1995@gmail.com` ➔ Bấm `Gửi mã`.
  3. Kết nối IMAP vào `imap.gmail.com:993` với thông tin cấu hình từ `OTP_MAIL_USER` và `OTP_MAIL_APP_PASSWORD` để lấy mã OTP 6 số do Microsoft gửi về (`account-security-noreply@accountprotection.microsoft.com`).
  4. Điền OTP vào 6 ô trên web ➔ Vượt qua màn hình passkey (bấm Back 1 lần) ➔ Chọn `Có` (Duy trì đăng nhập) để vào thẳng hộp thư `outlook.live.com/mail/0/inbox`.

## 3. Web Chrome vs App Outlook trên Android cũ (Samsung Galaxy S7)
- **App Outlook Android:**
  + Trên các dòng máy Android cũ (Android 8.0, Samsung S7), ứng dụng Outlook Android khi gõ email đăng nhập thường bị lỗi redirect sang màn hình `Tạo tài khoản Microsoft mới (@outlook.com.vn)`.
  + Gây lỗi `BLOCKED: OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND`.
- **Khắc phục chuẩn canonical:**
  + Bắt buộc dùng trình duyệt **Chrome (`com.android.chrome`)** qua luồng `login_web_legacy` để đăng nhập hộp thư Hotmail.
  + Khi đặt lại mật khẩu TikTok bằng email: Mở `https://www.tiktok.com/login/email/forget-password` trên Chrome (hoặc mở ẩn danh) để gửi mã OTP về Hotmail, nhập mật khẩu mới trực tiếp trên web TikTok, sau đó quay lại App TikTok đăng nhập thẳng.

## 4. Tránh xung đột namespace Python `core` giữa các repo
- **Sự cố:** Repo `Hotmail` và repo `tiktok-add-bao-mat-f2a/python_runner` đều có package con tên là `core`. Khi script thêm cả 2 repo vào `sys.path`, lệnh `from core.passwords import ...` sẽ gây `ModuleNotFoundError: No module named 'core.passwords'`.
- **Khắc phục:** Sử dụng `importlib.util.spec_from_file_location` nạp trực tiếp file `passwords.py` theo đường dẫn tuyệt đối, không dựa vào `sys.path` chung.

## 5. Kỷ luật chu kỳ Cronjob giãn cách TikTok (Anti Rate-Limit)
- Khi lập cronjob retry hoặc can thiệp hàng loạt vào tài khoản TikTok/Hotmail trên máy:
  + CẤM đặt chu kỳ quá ngắn (`*/15 * * * *` hoặc `*/5 * * * *`) dễ gây kích hoạt rate-limit bảo mật thiết bị của TikTok.
  + BẮT BUỘC đặt chu kỳ giãn cách tối thiểu **1 tiếng 1 lần (`0 * * * *`)** để TikTok tự động làm mới và hạ ngưỡng phạt trust score.
  + Đảm bảo cấu hình `deliver: origin` để báo cáo đúng chat thread đang làm việc.
