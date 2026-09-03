# Drawer Verification & Shop Warranty Reporting for Hotmail (2026-08-20)

## 1. Phân loại lỗi đăng nhập & Báo shop bảo hành
Khi chạy batch nạp Hotmail từ shop, cần phân loại chính xác lỗi trước khi báo bảo hành:
- **Lỗi Sai Mật Khẩu (Đủ điều kiện bảo hành):**
  - Màn hình Microsoft WebView hiện cảnh báo đỏ: `! Mật khẩu đó không đúng với tài khoản Microsoft của bạn.`
  - **Định dạng báo shop:** User yêu cầu CHỈ gửi `email|password`, tuyệt đối không gửi kèm chuỗi `refresh_token` hay `client_id` dài dòng.
- **Lỗi Hạ Tầng / Proxy Timeout (KHÔNG tính là sai pass):**
  - Toast *"Hiện không thể thêm tài khoản này."* xuất hiện ngay tại màn hình nhập email (`AddAccountActivity`) trước khi sang form password.
  - Khắc phục: Kiểm tra IP live qua proxy/VPN, chuyển tài khoản sang máy khác có proxy sống.
- **Tài khoản OAuth2 Shop Loại 2:**
  - `refresh_token` kiểm tra qua Graph API `https://login.microsoftonline.com/consumers/oauth2/v2.0/token` + `/me/messages` trả về `200 OK`.
  - Token đọc OTP độc lập với việc đăng nhập qua app Outlook.

## 2. Quản lý trạng thái kho tài khoản (TXT ↔ Excel)
- **Nguồn cấp:** File TXT `hotmail_input.txt` (dạng `email|pass|token|client_id`).
- **Nơi ghi kết quả:** `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (Sheet `Gmail Accounts`).
- **Quy tắc đồng bộ:**
  - Tài khoản **đăng nhập thành công vào Inbox Outlook**: Ghi ngay vào file Excel (kèm Cột 8 ngày nạp, Cột 9 Token, Cột 10 ClientID) và **XÓA KHỎI file TXT**.
  - Tài khoản **chưa xong / lỗi**: **GIỮ NGUYÊN trong file TXT**, tuyệt đối không ghi nhận thành công trong Excel.

## 3. Kỹ thuật Drawer Verification trong `flows/hotmail_login.py`
Khi xác thực tài khoản sau khi nạp mật khẩu:
- **Bẫy `_outlook_app_verify_and_write`:**
  - Nếu app đang mở sẵn Navigation Drawer (hoặc Inbox Zero rỗng không có `messages_listview`), logic cũ cố gọi `_outlook_app_open_inbox_from_archive` dẫn đến lỗi `OUTLOOK_APP_DRAWER_INBOX_TARGET_NOT_FOUND`.
  - **Fix chuẩn:** Kiểm tra `if not _outlook_app_drawer_open(xml)` trước khi điều hướng Archive; nếu drawer đã mở sẵn thì bỏ qua bước mở drawer từ nút `account_button`, sau đó đối chiếu `outlook_app_identity_matches` trực tiếp trên XML drawer hiện tại.
