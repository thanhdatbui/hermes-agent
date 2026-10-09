# Quy trình Đổi Thông Tin Hotmail Chống Bên Bán Back & Xuất Bán (2026-09-17)

## 1. Bối cảnh & Nghiệp vụ xuất bán cả cụm (TikTok + Hotmail)
- Nick TikTok trên farm liên kết với Hotmail gốc mua từ shop.
- **Rủi ro:** Nuôi tài khoản TikTok lâu ngày nếu không đổi thông tin Hotmail sớm thì bên bán mail có thể dùng pass cũ hoặc mail khôi phục tạm (`getnada`/`tempmail`) để back lại hòm thư và chiếm đoạt TikTok.
- **Yêu cầu kinh doanh:** Khi bán tài khoản TikTok cho khách, bắt buộc bán kèm cả hòm thư Hotmail gốc.
- **Nguyên tắc "Sạch bóng info":**
  1. **TUYỆT ĐỐI KHÔNG gán email cá nhân/mail khôi phục của farm vào Hotmail.** Nếu dính mail khôi phục của chủ farm, khách mua sẽ không đổi được thông tin hoặc khiếu nại tài khoản dính chủ cũ.
  2. Hotmail bàn giao phải trắng tinh, chỉ gồm: **`EMAIL | PASS_MỚI`**.

## 2. Vì sao KHÔNG cần sinh lại `refresh_token` sau khi đổi pass Hotmail?
- Trước đây cần `refresh_token` vì TikTok chưa bật 2FA Authenticator, mỗi lần login/đổi info TikTok bắt nhận OTP qua mail $\rightarrow$ cần token để gọi Graph API đọc mã nhanh.
- Sau khi tài khoản TikTok đã được kích hoạt **2FA Authenticator (TOTP Secret 32 ký tự)**:
  + Đăng nhập TikTok hoàn toàn bằng: `User + Pass TikTok + Mã TOTP 6 số`.
  + TikTok **KHÔNG CÒN gửi bất kỳ mã OTP nào về Hotmail nữa**.
  + Do đó, sau khi đổi pass Hotmail, việc mất hiệu lực token cũ không ảnh hưởng đến vận hành farm. **Không cần tốn công sinh lại token mới qua OAuth2 / Chrome.**

## 3. Quy trình Đổi Info Hotmail 3 Bước (Safe & Clean)
Chạy script tự động hóa trên Chrome của máy Android (qua đúng Proxy 4G của máy để tránh checkpoint Microsoft):

### Bước 1: Đăng nhập Web (`login_web_legacy`)
- Mở Chrome trên máy S7 tới `https://login.live.com` qua proxy thiết bị.
- Điền `email` và `current_password` (pass cũ của shop).
- Bắt buộc kiểm tra đăng nhập thành công vào session trước khi chuyển sang trang bảo mật.

### Bước 2: Đổi Mật Khẩu (`task_change_password`)
- Mở URL `https://account.live.com/password/change`.
- Sinh mật khẩu ngẫu nhiên mạnh mới (14 ký tự gồm chữ hoa, chữ thường, số, ký tự đặc biệt).
- Điền `old_password` $\rightarrow$ `new_password` $\rightarrow$ `confirm_new_password` $\rightarrow$ Bấm Save.
- **Hệ quả tức thì:** Microsoft revoke 100% token cũ và session cũ của bên bán.

### Bước 3: Gỡ mail khôi phục rác & Đăng xuất mọi nơi (`Logout Everywhere`)
- Kiểm tra mục Advanced Security: Nếu bên bán có cài mail khôi phục rác tạm bợ (`getnada`, `tempmail`, `fvia`...), bấm Remove $\rightarrow$ Confirm gỡ sạch.
- Bấm **"Sign out everywhere" (Đăng xuất ở mọi nơi)** để hủy mọi phiên đăng nhập còn sót lại trên thiết bị của bên bán.
- Cập nhật pass mới vào Cột G (`PASS_MAIL`) của Excel `taikhoan_dat_v2_updated .xlsx`.

## 4. Bộ thông tin hoàn chỉnh bàn giao khách
$$\text{ID TikTok} \;\;|\;\; \text{Pass TikTok} \;\;|\;\; \text{Secret 2FA (TOTP)} \;\;|\;\; \text{Hotmail} \;\;|\;\; \text{Pass Hotmail Mới}$$
- Farm nuôi an tâm bằng 2FA TOTP.
- Khách nhận full combo sạch sẽ, tự add SĐT/mail khôi phục của riêng họ.
