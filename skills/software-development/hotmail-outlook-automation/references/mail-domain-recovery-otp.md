# Mail Khôi Phục Domain Riêng & Pipeline Đổi Pass Hotmail (fviainboxes.com, smvmail.com...)

## 1. QUY TẮC CỐT LÕI (INVARIANT)
- **CẤM TUYỆT ĐỐI** thấy mail khôi phục dạng domain lạ (`fviainboxes.com`, `smvmail.com`, `10mail.org`...) mà kết luận là "mail ảo không mở được", "server nội bộ", hay bỏ cuộc.
- Các domain này của shop MMO thực chất là các dịch vụ Temp Mail mở, có giao diện web và API công khai 100%.
- **ĐIỀU KIỆN ĐỦ ĐỂ CHANGE PASS (DUAL-OAUTH ELIGIBILITY GATE - 2026-10-08):**
  - Tài khoản Hotmail **CHỈ ĐỦ ĐIỀU KIỆN CHANGE PASS** khi đã thỏa mãn đồng thời:
    1. Đã đăng ký thành công Codex qua 5SIM/ChatGPT.
    2. Đã nạp và kích hoạt OAuth Codex lên **OmniRoute (:20129)** (kiểm tra SQLite `provider_connections` có `provider='codex'`).
    3. Đã nạp và kích hoạt OAuth Codex lên **9Router (:20128)** (kiểm tra SQLite `providerConnections` có `provider='codex'`).
  - Mục đích: Đảm bảo tài khoản đã khai thác trọn vẹn quota Codex cho cả 2 proxy LLM trước khi đổi mật khẩu làm đứt token/session. Thiếu 1 trong 2 server -> CẤM chuyển sang stage `CHANGE_INFO`.

## 2. Dịch Vụ fviainboxes.com & API Bóc OTP
- Web giao diện: `https://fviainboxes.com/` (truy cập trực tiếp trên GPM profile hoặc trình duyệt).
- **API Backend không cần auth/token:**
  - **Lấy danh sách thư:**
    `GET https://fviainboxes.com/messages?username={username}&domain={domain}`
    Ví dụ: `GET https://fviainboxes.com/messages?username=murtaghshandy1563pf&domain=fviainboxes.com`
    Trả về JSON: `{"result": [{"id": "...", "subject": "Your single-use code", "createdAt": 1791412944}]}`
  - **Lấy nội dung chi tiết & bốc OTP:**
    `GET https://fviainboxes.com/message?username={username}&domain={domain}&id={id}`
    Trả về body text/HTML, bóc tách Regex `(\d{6,7})` là lấy được OTP Microsoft ngay lập tức.
- **Helper module trong repo:**
  - `D:\Taadaa\Hotmail\scripts\mail_domain_otp_helper.py`
  - Hàm: `get_otp_from_fviainboxes(recovery_email, timeout_seconds=40)`

## 3. Quy Trình Change-Info & Sign Out Everywhere An Toàn
1. **Verify Identity:**
   - Khi vào `account.live.com/password/change`, Microsoft bắt xác thực qua mail khôi phục:
   - Điền đầy đủ địa chỉ mail khôi phục vào `#proof-confirmation-email-input` -> click *Send code*.
   - Gọi helper lấy OTP từ `fviainboxes.com` -> nhập vào các ô OTP (`#codeEntry-0` đến `#codeEntry-5`).
   - Xử lý vượt các màn hình trung gian nếu có: "We're updating our terms" (click Next), "Microsoft account notice" (click OK), "Stay signed in?" (click Yes).
2. **Submit New Password:**
   - Điền mật khẩu mới mạnh vào `#iPassword` và `#iRetypePassword` -> bấm submit `#UpdatePasswordAction` (hoặc nút Save).
3. **Đá Mail Khôi Phục (Remove Recovery Email) & Thay Thế Bằng Mail Domain Random:**
   - Vào `https://account.live.com/proofs/manage/additional`.
   - **LƯU Ý:** Nếu tài khoản chỉ có 1 mail khôi phục, Microsoft sẽ chặn không cho xóa trực tiếp (*"You need to add an email address before you can remove..."*).
   - **QUY TRÌNH THAY THẾ CHUẨN:**
     1. Tạo 1 mail ngẫu nhiên mới cùng domain (VD: `kbtad_xxx@fviainboxes.com`).
     2. Bấm *Add another way to sign in to your account* -> chọn *Email a code*.
     3. Nhập mail mới -> lấy OTP từ API `fviainboxes.com` -> verify hoàn tất.
     4. Sau khi mail mới đã kích hoạt, tiến hành bấm `Remove` mail khôi phục cũ của bên bán và xác nhận.
     5. Cập nhật mail khôi phục mới vào Master Database / Excel (`gmail_clean_v2.xlsx`).
   - Việc thay bằng mail domain random ngăn chặn 100% bên bán back acc qua form Forgot Password (vì MS bắt gõ đúng 100% địa chỉ mail ẩn), đồng thời khách mua nick sau này vẫn lấy được OTP dễ dàng qua web `fviainboxes.com` mà không vướng 2FA Authenticator.
4. **Sign Out Everywhere (Hủy token cũ của bên bán):**
   - Click `#DeleteTrustedDevices` ("Sign out everywhere").
   - Xác nhận modal -> Microsoft phản hồi *"We've started signing you out. In the next 24 hours..."*.
5. **Đăng Xuất & Re-login Kiểm Chứng Bằng Mật Khẩu Mới:**
   - Điều hướng sang `https://login.live.com/logout.srf` để clear session cũ.
   - Đăng nhập lại từ đầu bằng mật khẩu mới vừa đổi để đảm bảo mật khẩu đã ăn vào hệ thống Microsoft.
   - Chú ý Fluent UI: Selector ô password có thể là `#passwordEntry` (name `passwd`) thay vì `#i0118`.
   - Chụp ảnh màn hình trang chủ `account.microsoft.com` làm bằng chứng nghiệm thu (Checkpoint).
