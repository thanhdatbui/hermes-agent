# BoxTaiKhoan Hotmail OAuth2 Purchase & Deferred Tracking Apply

## 1. Mua Hotmail OAuth2 tự động qua API BoxTaiKhoan
- **Endpoint:** `https://boxtaikhoan.com/ajaxs/client/product.php` (Method: POST)
- **Headers:**
  - `User-Agent: Mozilla/5.0 ...`
  - `Content-Type: application/x-www-form-urlencoded`
  - `X-Requested-With: XMLHttpRequest`
- **Payload:**
  - `action`: `buyProduct`
  - `id`: `60` (Product 60: Hotmail Trust OAuth2)
  - `variant_id`: `0`
  - `amount`: `<số lượng cần mua>`
  - `coupon`: `""`
  - `api_key`: `a0ed850f635d5c7042e89f68b41476bb` (hoặc lấy từ config/session)
  - `user_input`: `{}`
- **Kết quả trả về:**
  - JSON format: `{"status": "success", "msg": "Tạo đơn hàng thành công!", "trans_id": "...", "data": ["email|pass|refresh_token|client_id", ...]}`
  - Token hợp lệ dài >450 ký tự, có thể đổi ngay lấy Graph Access Token qua `login.microsoftonline.com/consumers/oauth2/v2.0/token`.

## 2. Quy trình nạp mail vào `gmail_clean_v2.xlsx`
- Lưu ý bảo tồn cấu trúc bảng: 11 cột:
  `[STT, Email, Password, None, None, None, None, 'YYYY-MM-DD', RefreshToken, ClientID, Status]`
- Cột STT ép kiểu `int`, sắp xếp theo `(STT, Email)` tăng dần.
- Giữ định dạng font `Calibri 11pt`, căn giữa cột STT, Date, Status.

## 3. Quy trình Apply Deferred Tracking Results & Sync Safe Workbook
- Sau khi `_run_all_targets.py` hoàn thành:
  1. Tìm các file `tracking_result_stt<N>_*.json` trong thư mục `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<run_id>\batch_*\stt_*\`.
  2. Chạy lệnh:
     ```bash
     python scripts/apply_deferred_tracking_results.py <path_to_json_1> <path_to_json_2> ...
     ```
  3. Đồng bộ lại sang `taikhoan_run_safe.xlsx`:
     ```bash
     python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py"
     ```
  4. Kiểm tra đảm bảo serial mapping trên `taikhoan_run_safe.xlsx` khớp đúng với phần cứng ADB thật của 80 máy.
