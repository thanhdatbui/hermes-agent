# Hotmail Rotation, Clean Delivery, and TikTok Linked Email Migration (2026-09-18)

## 1. Bản Chất 2FA Email Trên TikTok & Chống Bên Bán Back
- **Tắt 2FA Email trên TikTok:** Với tài khoản TikTok không có số điện thoại (no-phone), server TikTok v46+ luôn ép giữ phương thức `Email: Bật` (Toast: *"Không thể thay đổi cài đặt vì lý do bảo mật, hãy thử lại sau"*). Không cần ép gỡ vì khi đã có 2FA Authenticator (TOTP Secret 32 ký tự), khi đăng nhập máy khác TikTok chỉ yêu cầu mã TOTP + Mật khẩu, hoàn toàn không gửi mã về mail. Hơn nữa, khi bán nick cho khách bắt buộc phải bàn giao kèm Hotmail gốc; nếu gỡ mail ra thì sau này xuất bán lại phải mất công add lại.
- **Chống bên bán Hotmail back:** Nguy cơ bị back nằm ở bên bán Hotmail. Giải pháp triệt để là **đổi mật khẩu Hotmail và đăng xuất mọi nơi**, không phải cố gỡ email trên TikTok.

## 2. Token Graph API vs Mật Khẩu Mới
- Khi đổi mật khẩu Microsoft/Hotmail, toàn bộ OAuth `refresh_token` cũ bị revoke (hủy hiệu lực) 100%.
- Không cần sinh lại `refresh_token` mới sau khi đổi pass vì TikTok đã có 2FA TOTP. Tài khoản chỉ cần tồn tại dưới định dạng chuẩn sạch:
  $$\text{Hotmail} \;\;|\;\; \text{Pass Hotmail Mới}$$
- Bên bán mất quyền truy cập vĩnh viễn vì mật khẩu cũ và token cũ đều die.

## 3. Thứ Tự Vận Hành Tử Huyệt (Chrome First -> Outlook After)
- **CẤM:** Đăng nhập App Outlook trên điện thoại trước rồi mới vào Chrome đổi pass + bấm "Đăng xuất khỏi mọi thiết bị" (Sign out everywhere). Làm ngược sẽ khiến App Outlook trên máy S7 bị văng session ngay lập tức.
- **QUY TRÌNH CHUẨN:**
  1. Mở Chrome trên máy S7 (có proxy 4G của máy) -> Vào `account.live.com/password/change`.
  2. Đổi sang mật khẩu ngẫu nhiên mạnh mới.
  3. Gỡ bỏ mail khôi phục rác của bên bán (nếu có).
  4. Bấm **Đăng xuất khỏi mọi thiết bị (Sign out everywhere)** để thu hồi toàn bộ session cũ của bên bán.
  5. Cập nhật pass mới vào Cột G (`PASS_MAIL`) của Excel `taikhoan_dat_v2_updated .xlsx`.
  6. Mở App Outlook trên máy S7 -> Đăng nhập bằng Mật khẩu Mới vừa đổi để nhận phiên làm việc chính chủ vĩnh viễn.

## 4. Kỷ Luật Bàn Giao Khách (Clean Delivery - Cấm Dính Mail Khôi Phục Cá Nhân)
- Khi đổi pass Hotmail để nuôi và xuất bán:
  + Tuyệt đối **KHÔNG gán mail khôi phục cá nhân/farm** vào Hotmail nếu sau này có kế hoạch bán cả cụm TikTok + Hotmail cho khách.
  + Giữ Hotmail ở trạng thái sạch trắng: `EMAIL | PASS_MỚI` (không gắn SĐT hay mail khôi phục ngoài).
  + Khách nhận acc tự cầm hòm thư gốc, tự add mail/SĐT của khách mà không bị vướng mắc tranh chấp.

## 5. Đổi Email Liên Kết Trên TikTok Cho Các Nick Cổ (Dính Recovery Cũ)
- Với dàn nick cổ (tạo từ tháng 02-03/2026 dính mail khôi phục cũ như `khoale`):
  + Khi cần tách hẳn để bán, không cần chờ lấy OTP mail cũ.
  + Vào TikTok -> `Hồ sơ` -> `Cài đặt và quyền riêng tư` -> `Tài khoản` -> `Email` -> Chọn `Thay đổi email`.
  + Vượt gate xác minh tài khoản hiện tại bằng chính **Secret Key 2FA TOTP (Cột E)** hoặc Mật khẩu TikTok (Cột D) mà không cần chạm vào Hotmail cũ.
  + Nhập Hotmail mới mua trắng tinh -> Nhận OTP từ Hotmail mới để hoàn tất đổi email -> Cập nhật Cột F và G Excel.
  + Script runner canonical: `D:\Taadaa\Hotmail\scripts\tiktok_change_linked_email_runner.py`.
