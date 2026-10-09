# TikTok Change Linked Email Direct Bypass & Hotmail API Replacement (18/09/2026)

## Bối cảnh & Hiện tượng phát hiện thực tế (Máy 2 - `thanh.h.dng00`)
- **Tình huống:** Farm có 51 tài khoản TikTok cổ (tạo từ tháng 3/2026) đang gắn email dính líu đến email khôi phục lạ (`khoaleemagic@gmail.com`). Khi cố đổi mật khẩu email qua giao diện web Microsoft, hệ thống bắt gửi OTP về mail khôi phục này.
- **Giải pháp dứt điểm:** Thay vì phụ thuộc vào việc xin OTP mail cũ, thực hiện đổi thẳng **Email liên kết trên TikTok** sang Hotmail mới mua qua API shop (`buy_hotmail.py`).
- **Phát hiện bước ngoặt trên TikTok UI:**
  - Khi điều hướng: `Hồ sơ` -> Menu 3 gạch (`[948, 96][1056, 204]`) -> `Cài đặt và quyền riêng tư` -> `Tài khoản` -> `Thông tin tài khoản` -> `Email` -> Bấm **"Thay đổi email"** (`[120, 1291][960, 1434]`).
  - Trên các tài khoản **đã bật 2FA Authenticator (TOTP)** và đã đăng nhập lâu ngày trên thiết bị, TikTok **KHÔNG HỀ bắt xác minh qua email cũ** và cũng không hiển thị gate challenge OTP mail cũ.
  - TikTok **MỞ THẲNG MÀN HÌNH "Nhập email" MỚI** (ô input tại `[162, 570][918, 630]`, nút "Tiếp tục" tại `[96, 735][984, 891]`).

## Quy trình tự động hóa chuẩn (End-to-End)
1. **Mua Hotmail mới qua API:**
   - Sử dụng script `D:\Taadaa\tools\buy_hotmail.py --buy 1 --target-file <path>`.
   - Lấy định dạng: `email|password|refresh_token|client_id`.
   - Xác thực refresh_token qua Graph API `https://graph.microsoft.com/v1.0/me/messages` đảm bảo kết nối hòm thư HTTP 200 trước khi nạp vào máy.
2. **Điều hướng TikTok trên thiết bị S7:**
   - Đảm bảo tài khoản mục tiêu đang active (nếu không, mở Account Switcher tại header để chuyển đúng nick).
   - Tap menu 3 gạch (`(1002, 150)`), tap "Cài đặt và quyền riêng tư" (`(623, 1248)`).
   - Tap "Tài khoản" (`(540, 1791)`), tap "Thông tin tài khoản" (`(540, 324)`).
   - Tap dòng "Email" (`(540, 480)`), tap "Thay đổi email" (`(540, 1362)`).
3. **Nhập Email mới & lấy OTP Graph API:**
   - Nhập Hotmail mới qua `input text <new_email>`.
   - Tap "Tiếp tục" (`(540, 813)`).
   - TikTok chuyển sang màn hình "Nhập mã gồm 6 chữ số".
   - Polling Microsoft Graph API (mỗi 3-5s trong tối đa 60s) để trích xuất 6 chữ số OTP từ thư gửi về từ TikTok.
   - Nhập OTP qua `input text <otp>` hoặc `keyevent KEYCODE_NUM`.
4. **Đồng bộ Workbook Excel:**
   - Cập nhật Hotmail mới vào Cột F (`GMAIL`/`EMAIL`).
   - Cập nhật Mật khẩu Hotmail mới vào Cột G (`PASS_MAIL`).
   - Giữ nguyên các cột ID (C), Pass TikTok (D), và Secret Key 2FA TOTP (E).

## Pitfalls & Quy tắc bất biến
- **Không bao giờ gắn mail khôi phục cá nhân:** Hotmail mua về bán trọn bộ kèm nick cho khách, giữ mail ở trạng thái sạch ("Clean Delivery").
- **Dọn tiến trình `app_process` trước khi dump UI:** Nếu `uiautomator dump` bị timeout 600s hoặc exit code 137, kiểm tra và kill các tiến trình zombie `app_process` đang giữ socket độc quyền trước khi thử lại.
