# Hướng Dẫn Mua & Trích Xuất Token Hotmail BoxTaiKhoan.com

## 1. Cơ chế API Mua Tài Khoản
- **Endpoint**: `POST https://boxtaikhoan.com/ajaxs/client/product.php`
- **Product ID**: `60` (Tài Khoản Hotmail Trust - OAuth2 IMAP/POP3/GRAPH, 393đ).
- **Tham số**:
  - `action`: `buyProduct`
  - `id`: `60`
  - `variant_id`: `0`
  - `amount`: `1`
  - `api_key`: `[REDACTED_API_KEY]`
  - `user_input`: `{}`
- **Quy tắc mua lẻ từng acc (`amount=1`)**:
  - Khi mua `amount=1`, API trả về trực tiếp mảng JSON `data: ["email|pass|refresh_token|client_id"]`.
  - Giúp lấy ngay chuỗi token mà không phải crawl web.

## 2. Trích Xuất Dữ Liệu Từ Lịch Sử Đơn Hàng Web (`/product-orders/`)
Khi cần lấy lại tài khoản từ các đơn đã mua trên web:
1. **Khởi chạy Chrome thật của User với port Debug**:
   ```bash
   cmd.exe /c start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\Kibe\AppData\Local\Google\Chrome\User Data" --profile-directory="Profile 4"
   ```
2. **Cấu trúc DOM trang chi tiết đơn (`/product-order/<trans_id>`)**:
   - Dòng tài khoản nằm trong:
     - `document.querySelector('textarea.account-field').value`
     - Hoặc `document.querySelector('input.checkbox_product_sold').getAttribute('data-checkbox')`
3. **Định dạng & Tiêu chuẩn Token**:
   - Định dạng: `email|password|refresh_token|client_id`
   - Chiều dài `refresh_token`: 450 - 525 ký tự (chuẩn 457 ký tự).
   - `client_id`: Mặc định `9e5f94bc-e8a4-4e73-b8be-63364c29d753` nếu thiếu.

## 3. Quy Trình Kiểm Chứng Live Token (Bắt Buộc)
- Trước khi nạp bất kỳ dòng nào vào `gmail_clean_v2.xlsx`:
  - Gọi `hotmail_provider.exchange_refresh_token(refresh_token, client_id)`.
  - Phải nhận về `access_token` hợp lệ (status 200 từ Microsoft).
  - Nếu token lỗi (`status 400 AADSTS70000` hoặc token bị cắt ngắn):
    - Không nạp vào `gmail_clean_v2.xlsx`.
    - Cách ly vào `D:\Taadaa\Hotmail\hotmail_failed_quarantine.txt` để đối soát khiếu nại shop.
