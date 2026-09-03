# Marketplace Hotmail Token Validation & CMSNT/ShopClone Quirks

## 1. Microsoft OAuth2 Refresh Token Validation & Truncation Pitfall
- **Chuẩn cấu trúc Token hợp lệ**:
  - Microsoft OAuth2 Refresh Token (MSA Artifacts / Graph API) chuẩn có độ dài từ **450 – 550 ký tự** (bắt đầu bằng `M.C5...` và kết thúc bằng chuỗi hash base64 không chứa dấu `$`).
  - Client ID chuẩn: `9e5f94bc-e8a4-4e73-b8be-63364c29d753` (Thunderbird) hoặc Client ID đăng ký trên Azure Portal.
- **Lỗi cắt cụt Token trên các sàn clone (ShopClone/CMSNT)**:
  - Một số sàn/shop (như `clonefbig.com` gói `ID 3470`) thiết lập cột CSDL dạng `VARCHAR(100)`, dẫn đến toàn bộ Refresh Token khi nạp vào kho bị cắt cụt còn đúng **101 ký tự** (kết thúc bởi ký tự `$`).
  - Khi gửi request đổi Access Token sang Microsoft (`https://login.microsoftonline.com/common/oauth2/v2.0/token`), máy chủ Microsoft sẽ từ chối ngay với lỗi:
    `AADSTS70000: The provided value for the input parameter 'refresh_token' or 'assertion' is not valid.`
- **Quy tắc kiểm tra bắt buộc trước khi nạp kho (`gmail_clean_v2.xlsx`)**:
  - Luôn kiểm tra độ dài token: `len(token) >= 400`.
  - Chạy hàm `exchange_refresh_token(refresh_token, client_id)` thử nghiệm trước khi mua số lượng lớn hoặc nạp vào bảng master.

---

## 2. CMSNT / ShopClone7 Authentication & Session Handling
- **Lỗi Quên Mật Khẩu do thiếu SMTP**:
  - Rất nhiều site clone không cấu hình máy chủ gửi mail SMTP. Khi bấm quên mật khẩu sẽ báo lỗi: *"Website chưa được cấu hình SMTP, vui lòng liên hệ Admin"*.
- **Quy tắc Đổi Mật Khẩu Profile (`ChangePasswordProfile`)**:
  - Mã nguồn CMSNT bắt buộc phải cung cấp `password` (mật khẩu hiện tại) đúng thì mới cho cập nhật `newpassword`.
- **Cơ chế phục hồi phiên bằng Cookie qua Chrome CDP**:
  - Khi mất/quên mật khẩu nhưng còn lưu phiên hoặc có cookie `PHPSESSID` / `token`, nạp cookie trực tiếp vào session CDP (`Network.setCookie`) để truy cập thẳng dashboard, lịch sử đơn hàng (`/product-orders`) và số dư mà không cần xác thực mật khẩu lại.
