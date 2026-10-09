# Quy trình phục hồi nick cũ & Xử lý 2FA Email OTP chống Magic Link (2026-09-17)

## 1. Bối cảnh & Hiện tượng
Khi tài khoản cũ (Row 1 các máy farm) bị mất session trên Switcher nhưng thiết bị còn lưu cache trong danh sách "Chào mừng bạn trở lại" (One-Tap Fast Login), hoặc khi nhập lại email/password:
- TikTok kích hoạt màn hình **Xác minh 2 bước** đòi mã OTP gửi về Email (Hotmail/Outlook) hoặc Authenticator App (2FA TOTP).
- **CẢNH BÁO RATE LIMIT & MAGIC LINK:** Nếu bot/người vận hành nhập mật khẩu hoặc kích hoạt gửi mã OTP mà bỏ dở không nhập mã ngay, chỉ sau 1–2 lần TikTok sẽ tự động chuyển cơ chế xác thực sang **Magic Link qua email** hoặc áp đặt **Rate limit 900 giây (15 phút)**, làm tê liệt khả năng login tự động.

## 2. Quy tắc hành động dứt khoát (No-Stall Rule)
- **TUYỆT ĐỐI KHÔNG DỪNG LẠI HỎI USER KHI ĐANG Ở MÀN HÌNH 2FA:** Khi TikTok đã gửi mã về mail, phải chủ động lấy mã OTP tươi và điền ngay lập tức.
- **Trình tự ưu tiên 2 tầng xác minh:**
  1. **Tầng 1 (2FA TOTP App):** Nếu màn hình hiển thị "Ứng dụng xác thực", kiểm tra cột 2FA Secret trong Master DAT (`taikhoan_dat_v2_updated .xlsx`), sinh mã bằng `automation_core.totp.generate_totp(secret)` và điền trực tiếp.
  2. **Tầng 2 (Email Hotmail/Outlook App):** 
     - Mở ứng dụng Outlook trên thiết bị hoặc qua Graph API.
     - Nếu Outlook chưa có tài khoản, đăng nhập nhanh qua giao diện Outlook bằng password trong DAT (`Tài Khoản!G`), vượt qua các bước giới thiệu (bấm *Tiếp theo* -> *Chấp nhận* -> *Tiếp tục với Outlook*).
     - Vuốt làm mới hòm thư đến, lấy mã 6 chữ số từ email mới nhất của TikTok.
     - Quay lại TikTok, điền mã OTP 6 số và nhấn **Tiếp tục**.

## 3. Quy tắc đối soát slot Switcher trước khi can thiệp
- **Không vội vàng logout nick mới:** Rất nhiều trường hợp máy hiển thị lỗi thiếu nick Row 1 không phải do máy đầy 8 nick, mà thực tế chỉ có 6–7 nick trên Switcher (vẫn còn nguyên nút *"Thêm tài khoản"*).
- **Rà soát nick mồ côi:** Chỉ tiến hành logout khi máy đã chạm trần 8 nick, và bắt buộc ưu tiên logout các nick mồ côi từ đợt chạy cũ (đã đối soát có đủ backup Pass + Mail trong file lưu trữ), tuyệt đối không logout nick mới reg chưa có 2FA để tránh nguy cơ checkpoint mất nick vĩnh viễn.
