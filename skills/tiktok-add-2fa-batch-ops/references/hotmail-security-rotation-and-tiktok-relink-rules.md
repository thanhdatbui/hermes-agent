# Quy Trình Quản Trị Bảo Mật Hotmail & TikTok: Chống Back Nick Khi Nuôi và Bán Khách (18/09/2026)

## 1. Bản Chất 2FA TikTok vs Hotmail Cũ
- **Không bao giờ cố gỡ xác thực Email trên TikTok v46+ (no-phone):** TikTok chặn cứng server-side ("Không thể thay đổi cài đặt vì lý do bảo mật"). Việc cố ép tắt Email làm runner văng lỗi `EMAIL_DISABLE_NOT_STABLE` vô ích.
- **Sau khi bật 2FA TOTP:** TikTok đăng nhập bằng `User + Pass TikTok + Mã TOTP 6 số (Secret Key)` $\rightarrow$ TikTok **không bao giờ gửi OTP về Hotmail nữa**.
- **Mối đe dọa bị bên bán mail back:** Nằm ở việc bên bán còn giữ password gốc hoặc refresh_token của Hotmail $\rightarrow$ Bắt buộc phải triệt hạ quyền truy cập của bên bán.

## 2. Quy Tắc Vàng: Đổi Pass Trực Tiếp Trên Web Trước, Đăng Nhập App Outlook Sau
- **Bẫy văng session:** Nếu đăng nhập vào App Outlook trên máy trước, khi vào trang quản trị Microsoft bấm **"Đăng xuất khỏi mọi thiết bị" (Sign out everywhere)**, session trên App Outlook sẽ bị Microsoft thu hồi (revoke) và văng ra ngoài ngay lập tức.
- **Thứ tự thực thi chuẩn:**
  1. Mở Chrome trên máy S7 (qua Proxy của máy) $\rightarrow$ Đăng nhập pass cũ.
  2. Vào `account.live.com/password/change` $\rightarrow$ Đổi sang **Mật khẩu mới mạnh**.
  3. Gỡ mail khôi phục rác của bên bán (nếu có).
  4. Bấm **"Đăng xuất ở mọi nơi" (Sign out everywhere)** $\rightarrow$ Đá văng 100% bên bán, hủy toàn bộ token cũ.
  5. Cập nhật mật khẩu mới vào Cột G (`PASS_MAIL`) của Excel `taikhoan_dat_v2_updated .xlsx`.
  6. Mở App Outlook trên máy S7 $\rightarrow$ Đăng nhập bằng Mật khẩu Mới $\rightarrow$ Giữ phiên sạch vĩnh viễn.

## 3. Không Cần Tạo / Sinh Lại Refresh Token Mới Khi Đã Có 2FA TikTok
- Trước đây cần Refresh Token vì cần gọi Microsoft Graph API đọc OTP TikTok khi chưa có 2FA.
- Khi TikTok đã có 2FA TOTP: Đăng nhập hoàn toàn bằng TOTP + Pass TikTok. Hotmail chỉ cần duy nhất định dạng chuẩn **`EMAIL | PASS_MỚI`** trong workbook để quản lý và bàn giao khách. Không cần sinh token mới hay lưu token phức tạp.

## 4. Tuyệt Đối Không Gắn Mail Khôi Phục Cá Nhân Vào Hotmail Farm
- Khi bán tài khoản TikTok kèm Hotmail cho khách, Hotmail phải ở trạng thái **trắng thông tin, không dính mail khôi phục hay SĐT cá nhân của chủ farm**.
- Nếu gắn mail cá nhân, khách mua về sẽ không đổi được info hoặc nghi ngờ tài khoản bị theo dõi/dính chủ cũ.

## 5. Giải Pháp Thoát Ly Toàn Bộ Cho Dàn Nick Cổ Dính Mail Khôi Phục Cũ
- Đối với các nick TikTok cổ (từ tháng 3/2026) đang liên kết với mail cũ bị kẹt gate OTP khôi phục:
  - **Không cần đi nhờ vả lấy mã OTP mail cũ.**
  - Vào TikTok: `Hồ sơ` $\rightarrow$ `Cài đặt và quyền riêng tư` $\rightarrow$ `Tài khoản` $\rightarrow$ `Thông tin người dùng` $\rightarrow$ `Email` $\rightarrow$ Chọn **"Thay đổi email"**.
  - Vượt qua bước xác minh tài khoản hiện tại bằng **Secret Key 2FA TOTP (Cột E)** hoặc Pass TikTok.
  - Tự động gọi API mua 1 Hotmail mới toanh (qua `buy_hotmail.py` - BoxTaiKhoan/CloneFBIG) $\rightarrow$ Nhập vào TikTok $\rightarrow$ Đọc OTP từ hòm thư mới qua Graph API để xác nhận.
  - Cập nhật Email mới + Pass mail mới vào Cột F và G Excel $\rightarrow$ Nick sở hữu mail mới độc lập 100%.
