# Mua và Nạp Hotmail BoxTaiKhoan Tự Động cho TikTok Reg

## 1. Mua Hotmail OAuth2 (Product 60) qua API BoxTaiKhoan

- **Endpoint:** `POST https://boxtaikhoan.com/ajaxs/client/product.php`
- **Headers:**
  - `Content-Type: application/x-www-form-urlencoded`
  - `X-Requested-With: XMLHttpRequest`
  - `User-Agent: Mozilla/5.0 ...`
- **Payload:**
  - `action`: `buyProduct`
  - `id`: `60` (Hotmail Trust OAuth2 IMAP/POP3/GRAPH Live)
  - `variant_id`: `0`
  - `amount`: `<số_lượng>`
  - `api_key`: `a0ed850f635d5c7042e89f68b41476bb` (hoặc lấy từ config)
  - `user_input`: `{}`
  - `coupon`: `""`

- **Response format:**
  - `status`: `"success"`
  - `data`: List các chuỗi định dạng `email|password|refresh_token|client_id` (hoặc `email|password|refresh_token` với client_id mặc định `9e5f94bc-e8a4-4e73-b8be-63364c29d753`).

## 2. Kiểm tra Refresh Token (Graph API)
- Sử dụng `hotmail_provider.exchange_refresh_token(refresh_token, client_id)` hoặc gọi Microsoft OAuth2 token endpoint:
  - `POST https://login.microsoftonline.com/consumers/oauth2/v2.0/token`
  - Body: `client_id`, `grant_type=refresh_token`, `refresh_token`.
- Token hợp lệ trả về `access_token` và scope `Mail.Read` / `IMAP.AccessAsUser.All`.

## 3. Nạp vào `gmail_clean_v2.xlsx`
- Sheet: `Gmail Accounts`
- Cột: `[STT, Email, Password, null, null, null, Status, Ngày nạp (YYYY-MM-DD), Refresh Token, Client ID, null]`
- Sắp xếp tăng dần theo `(int(STT), Email)`. Font: `Calibri 11pt`, căn giữa cột STT, Status, Ngày, căn trái Email/Pass/Token.

## 4. Xử lý Tránh Lỗi TARGET_INVENTORY_CONFLICT
- Khi sync safe workbook (`taikhoan_run_safe.xlsx`) từ `taikhoan_dat_v2_updated .xlsx`, đảm bảo cột 10 (Device ID / Serial) của các máy không bị ghi đè thành ngày tháng hoặc serial sai.
- Serial canonical cho máy 73-80:
  - 73: `ce12160c75f16b2605`
  - 74: `ce061606c21e153d03`
  - 75: `ce011711d4cd802905`
  - 76: `9885b64d56305a3731`
  - 77: `ce05160595e7953b04`
  - 78: `ce0916090a9d320a01`
  - 79: `ce0516059d279f3e03`
  - 80: `ce061606cd45950405`
- Sau khi chạy reg thành công, apply deferred tracking results bằng:
  `python scripts/apply_deferred_tracking_results.py <deferred_json_paths...>`
  rồi chạy `python scripts/sync-safe-workbook.py` để làm mới `taikhoan_run_safe.xlsx`.
