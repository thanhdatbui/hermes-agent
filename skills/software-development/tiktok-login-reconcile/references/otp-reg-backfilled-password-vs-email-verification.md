# Hotmail/OTP Reg Backfilled Password vs Email OTP Verification (2026-09-02)

## Bối cảnh & Hiện tượng (Incident Máy 10 & Đợt Reg 21/08)
- Khi thực hiện đăng nhập hoặc reconcile tài khoản TikTok tạo từ đợt reg qua Hotmail OTP/Magic Link (như đợt 21/08), tài khoản trên Excel `taikhoan_dat_v2_updated .xlsx` có:
  - Cột `PASS` (cột D): một mật khẩu sinh ngẫu nhiên (ví dụ `0vjTtaET@kF`)
  - Cột `GMAIL` (cột F): email Hotmail (`LyndiaSchlesinger2198@hotmail.com`)
  - Cột `PASS MAIL` (cột G): mật khẩu Hotmail (`jaokzc163830`)
- Khi đăng nhập bằng `ID` + `PASS` (cột D), TikTok báo lỗi: `Mật khẩu sai` (hoặc `Wrong password`).

## Root Cause
- Lúc đăng ký tài khoản qua luồng OTP/Magic Link của Hotmail, tài khoản được tạo trực tiếp bằng việc xác minh email mà **chưa đặt mật khẩu tĩnh** trên hệ thống TikTok.
- Quá trình chạy fix dữ liệu sau đó đã sinh mật khẩu mới và ghi vào file Excel master (tách biệt cột D và cột G), nhưng mật khẩu này **chưa từng được set trên server TikTok**.
- Do đó, tài khoản không thể đăng nhập bằng cặp `ID + Pass cột D`.

## Quy tắc xử lý chuẩn
1. **Ưu tiên đăng nhập bằng Email thay vì Username:**
   - Tại form đăng nhập TikTok, nhập thẳng email Hotmail (`LyndiaSchlesinger2198@hotmail.com`).
   - TikTok sẽ tự động nhận diện tài khoản OTP và mở màn hình *"Xác minh email: Sử dụng liên kết này hoặc nhập mã được gửi đến..."*.
2. **Đọc mã OTP qua XOAUTH2 IMAP trực tiếp (Fast-Path < 2s):**
   - Đọc `refresh_token` và `client_id` từ `gmail_clean_v2.xlsx` (cột 8 & 9).
   - Lấy `access_token` qua endpoint `https://login.microsoftonline.com/common/oauth2/v2.0/token` (scope `https://outlook.office.com/IMAP.AccessAsUser.All offline_access`).
   - Kết nối `imaplib.IMAP4_SSL('outlook.office365.com', 993)` với cơ chế `XOAUTH2` (`user=<email>\x01auth=Bearer <token>\x01\x01`) để đọc ngay mã 6 số từ subject/body mail TikTok mới nhất.
   - Nhập mã OTP vào màn hình xác minh để log in thẳng vào Switcher.

3. **Lưu ý về việc đặt mật khẩu trong Cài đặt (In-app Settings):**
   - Sau khi log in vào app, nếu vào *Cài đặt > Tài khoản > Mật khẩu*, TikTok sẽ mở màn hình SparkActivity yêu cầu *"Xác minh danh tính bằng Mật khẩu cũ"*.
   - Do nick reg qua OTP không có mật khẩu ban đầu nên không thể tạo pass qua form Cài đặt. Nick sẽ vận hành bền vững theo cơ chế Passwordless (xác thực qua Hotmail OTP khi login mới) và giữ session trong 6 slot Switcher.
