# Hotmail Password Rotation & No Recovery Email Policy (17/09/2026)

## 1. Nghiệp Vụ Chống Back & Bán Đứt Cho Khách
- **Bản chất tài khoản Hotmail mua từ shop:** Ban đầu mua dưới dạng `email | pass | refresh_token | client_id`. Sau khi dùng để đăng ký hoặc liên kết với TikTok, nguy cơ bị bên bán mail back là rất cao nếu để mật khẩu gốc quá lâu.
- **Tại sao không cần sinh lại `refresh_token` sau khi đổi pass:**
  + Khi tài khoản TikTok đã được Add 2FA (Authenticator App / TOTP secret 32 ký tự) và mật khẩu TikTok mạnh, TikTok **không bao giờ gửi OTP về Hotmail nữa** trong các lần đăng nhập thông thường (`User + Pass TT + Mã TOTP`).
  + Không còn nhu cầu dùng Graph API đọc mail tự động hàng ngày. Do đó, việc sinh lại `refresh_token` là không cần thiết.
- **Định dạng tài khoản mục tiêu:**
  + Đưa tài khoản Hotmail về định dạng đơn giản và chuẩn mực: `EMAIL | PASS_MỚI`.
  + Ghi mật khẩu mới vào Cột G (`PASS MAIL`) trong `taikhoan_dat_v2_updated .xlsx`.

## 2. Quy Tắc "Tuyệt Đối Không Gắn Mail Khôi Phục Cá Nhân"
- **Chỉ đạo của Operator:**
  + Tài khoản Hotmail này sau này sẽ **bán kèm trọn bộ với tài khoản TikTok** cho khách mua nick.
  + **CẤM TUYỆT ĐỐI** gắn email khôi phục cá nhân của chủ farm (ví dụ `thanhdatbui1995@gmail.com`) vào Hotmail. Nếu gắn vào, khách mua acc sẽ không thể đổi info hoặc acc bị vướng thông tin chủ cũ, gây rủi ro tranh chấp và mất giá trị tài khoản.
  + **Xử lý mail khôi phục:**
    * Nếu tài khoản có sẵn mail khôi phục rác của bên bán (`getnada`, `tempmail`, `fvia`...): Bấm gỡ bỏ (`task_remove_untrusted_recovery_emails`).
    * Nếu tài khoản không có mail khôi phục: Giữ nguyên trạng thái trống, chỉ đổi mật khẩu chính và bấm "Sign out everywhere" (`task_logout_devices`).

## 3. Luồng Thực Thi Chuẩn (Chạy trên Máy S7 có Proxy)
1. Mở Chrome trên máy S7 qua proxy của máy đó.
2. Điều hướng vào `https://account.live.com/password/change`.
3. Đổi mật khẩu từ pass cũ sang mật khẩu ngẫu nhiên mạnh mới.
4. Bấm `Sign out everywhere` (`task_logout_devices`) để đá toàn bộ session cũ và vô hiệu hóa token của bên bán.
5. Cập nhật mật khẩu mới vào cột G workbook Excel.
