# Chiến Lược Đổi Thông Tin Hotmail Chống Back & Đăng Nhập App Outlook (18/09/2026)

## 1. Bản Chất Nghiệp Vụ & Vì Sao Không Cần Tạo Token Mới
- **Trước đây cần Token OAuth2 (`refresh_token`):** Do TikTok chưa bật 2FA, mỗi lần login/đổi info bắt OTP mail -> Cần token để gọi Microsoft Graph API đọc OTP nhanh qua script.
- **Sau khi Add 2FA TikTok:**
  + Tài khoản TikTok đã có: `Mật khẩu TikTok mạnh` + `2FA Authenticator (TOTP Secret 32 ký tự)` + `Lưu thông tin đăng nhập`.
  + Đăng nhập TikTok chỉ cần: `User + Pass TikTok + Mã TOTP` (sinh từ Secret Key).
  + **TikTok không bao giờ gửi OTP về Hotmail nữa.**
- **Mục tiêu duy nhất của việc Đổi Pass Hotmail:** **CHỐNG BÊN BÁN BACK ACC.**
  + Đổi pass Hotmail -> Toàn bộ `refresh_token` và session cũ của bên bán bị Microsoft revoke (hủy) 100%.
  + Do đó: **HOÀN TOÀN KHÔNG CẦN SINH LẠI TOKEN MỚI CHO HOTMAIL.**

## 2. Thứ Tự Luồng Thực Thi Chuẩn: ĐỔI PASS TRƯỚC -> LOG OUTLOOK SAU
- **Bẫy thứ tự sai:** Nếu log vào App Outlook trước rồi mới chạy script đổi pass và bấm "Đăng xuất khỏi mọi thiết bị" (`Sign out everywhere`), Microsoft sẽ revoke luôn session trên app Outlook của máy S7 -> App Outlook bị văng và bắt nhập lại mật khẩu.
- **Thứ tự chuẩn không tì vết:**
  1. **Giai đoạn 1 (Đổi Pass trên Web qua Proxy máy S7):**
     - Mở Chrome trên máy S7 (đúng proxy của máy) -> Vào `https://account.live.com/password/change`.
     - Đổi mật khẩu sang chuỗi ngẫu nhiên mạnh mới.
     - Xóa mail khôi phục rác (`getnada`, `tempmail`...) nếu có.
     - Bấm **"Đăng xuất ở mọi nơi" (`Sign out everywhere`)**: Đá sạch toàn bộ máy/tool của bên bán. Bên bán mất quyền truy cập vĩnh viễn.
  2. **Giai đoạn 2 (Đồng bộ Excel):**
     - Lưu ngay Pass Mới vào Cột G (`PASS_MAIL`) của file Excel `taikhoan_dat_v2_updated .xlsx` (và `gmail_clean_v2.xlsx`).
  3. **Giai đoạn 3 (Đăng nhập App Outlook bằng Pass Mới):**
     - Mở App Outlook trên máy S7 -> Đăng nhập bằng `Email + Pass Mới vừa đổi`.
     - Phiên làm việc trên App Outlook trở thành chính chủ, ổn định, không bao giờ bị văng.

## 3. Quy Tắc Bán Đứt Cho Khách (Không Dính Mail Khôi Phục Cá Nhân)
- **Chỉ đạo của Operator:** Khi bán lại tài khoản TikTok kèm Hotmail, Hotmail đó cũng bán đứt luôn cho khách.
- **Quy tắc bất di bất dịch:**
  - **TUYỆT ĐỐI KHÔNG GÁN MAIL KHÔI PHỤC CÁ NHÂN** vào Hotmail khi đổi pass.
  - Hotmail sau khi hoàn tất chỉ tồn tại ở định dạng chuẩn sạch bóng: **`EMAIL | PASS_MỚI`**.
  - Khi xuất xưởng giao khách: Bàn giao trọn bộ `ID TikTok | Pass TikTok | Secret 2FA | Hotmail | Pass Hotmail mới`. Khách tự cầm hộp thư gốc và tự thêm bảo mật riêng của họ.

## 4. Pitfall Màn Hình Xác Minh Danh Tính (Identity Challenge kh*****@gmail.com)
- **Hiện tượng:** Khi mở trang đổi mật khẩu Microsoft trên một số tài khoản cũ của farm, Microsoft chặn lại:
  `Chúng tôi sẽ gửi mã đến kh*****@gmail.com. Để xác minh rằng đây là email của bạn, hãy nhập mã xác minh vào đây.`
- **Nguyên nhân:** Các tài khoản này trước đây đã bị gán mail khôi phục `khoaleemagic@gmail.com` / `khoalemagic@gmail.com`.
- **Xử lý:**
  + Với tài khoản mới tinh (chưa có mail khôi phục): Luồng đổi pass chạy thẳng không bị gate.
  + Với tài khoản đã dính `kh*****@gmail.com`: Bắt buộc phải lấy mã OTP từ hộp thư `khoaleemagic@gmail.com` để giải phóng gate trước khi đổi mật khẩu.
