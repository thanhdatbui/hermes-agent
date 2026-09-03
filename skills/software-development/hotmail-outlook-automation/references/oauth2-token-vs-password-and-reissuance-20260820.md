# Hotmail OAuth2 Shop Type 2: Token Scope, Password Verification & Token Re-issuance (2026-08-20)

## 1. Bản chất tài khoản Hotmail Shop Loại 2 (`mail|pass|refresh_token|client_id`)
- **Khác biệt cốt lõi:** Tài khoản loại 2 được cấp kèm `refresh_token` + `client_id` (scope `Mail.Read offline_access`) để truy xuất hòm thư trực tiếp qua Microsoft Graph API.
- **Tình trạng lệch mật khẩu:** Nhiều tài khoản loại 2 có `refresh_token` sống 100% (gọi `/me/messages` trả về HTTP 200 OK) nhưng mật khẩu văn bản đi kèm lại không khớp trên giao diện đăng nhập Microsoft (`"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"`).
- **Phân loại lỗi báo Shop:**
  - Chỉ những tài khoản hiện thông báo đỏ *"Mật khẩu đó không đúng..."* trên WebView Microsoft mới tính là lỗi sai pass để gửi shop bảo hành.
  - Lỗi Toast *"Hiện không thể thêm tài khoản này"* ở bước đầu nhập email thường do lỗi proxy/kết nối upstream của thiết bị, không quy kết là sai pass.

## 2. Giới hạn đổi mật khẩu & Quên mật khẩu qua Token
- **Token không đổi được pass:** Microsoft Graph API cho tài khoản cá nhân (Consumer) không hỗ trợ endpoint đổi mật khẩu. Scope `Mail.Read` chỉ cho phép đọc thư.
- **Không thể Quên mật khẩu (Reset pass):** Microsoft chỉ gửi mã OTP đặt lại mật khẩu về Mail khôi phục hoặc Số điện thoại bảo mật đã liên kết của shop.
- **Kết luận:** Muốn đổi pass sở hữu tài khoản bắt buộc phải có mật khẩu gốc đúng từ shop.

## 3. Cơ chế đúc lại Refresh Token mới sau khi đổi mật khẩu
Khi tài khoản đổi mật khẩu thành công, token cũ sẽ bị Microsoft thu hồi (revoke). Để tiếp tục đọc OTP tự động:
1. **Khởi tạo Device Code Flow:** Gửi request tới `https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode` kèm `client_id`.
2. **Xác thực trên IP máy farm:** Mở `microsoft.com/devicelogin` qua browser/proxy của chính thiết bị và đăng nhập bằng **mật khẩu mới** để tránh CAPTCHA.
3. **Lưu Token mới:** Ghi đè chuỗi `refresh_token` mới vào Cột 9 (`token`) trong `gmail_clean_v2.xlsx`.

## 4. Quản lý danh sách nguồn TXT và Excel
- Tài khoản đăng nhập thành công vào Outlook App $\rightarrow$ Ghi vào `gmail_clean_v2.xlsx` (kèm cột 9 `token`, cột 10 `client_id`) và **xóa khỏi file nguồn TXT**.
- Tài khoản chưa đăng nhập xong hoặc lỗi $\rightarrow$ **Giữ nguyên trong file nguồn TXT** với đầy đủ định dạng ban đầu để xử lý tiếp hoặc yêu cầu shop bảo hành.
