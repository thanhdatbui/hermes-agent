# BoxTaiKhoan.com API & Locked Batch Hotmail Login Workflow (2026-08-22)

## 1. Tự động hóa mua Hotmail qua API BoxTaiKhoan.com

Thay vì phụ thuộc vào Web UI / Cloudflare, BoxTaiKhoan hỗ trợ gọi API trực tiếp với `api_key`:

- **Kiểm tra thông tin tài khoản & Số dư:**
  `GET https://boxtaikhoan.com/api/profile.php?api_key=<API_KEY>`
  - Trả về JSON: `{"status": "success", "data": {"username": "...", "money": "..."}}`.
- **Lấy danh mục sản phẩm & ID:**
  `GET https://boxtaikhoan.com/api/products.php?api_key=<API_KEY>`
  - ID 60: `Tài Khoản Hotmail Trust - OAuth2 [IMAP/POP3/GRAPH] Live 12 đến 36 Months - Zin 100% - Còn Skip 7 Ngày` (393đ/acc, có token Graph API).
  - ID 129: `Tài Khoản Hotmail TRUSTED GraphAPI - Live Vĩnh Viễn, Mail Khôi Phục Fviainboxes` (262đ/acc, không kèm token OAuth2).
- **Mua sản phẩm tự động (Endpoint AJAX Client):**
  `POST https://boxtaikhoan.com/ajaxs/client/product.php`
  - Payload (form-urlencoded):
    ```python
    data = {
        'action': 'buyProduct',
        'id': '60',            # Product ID
        'variant_id': '0',
        'amount': '26',        # Số lượng cần mua
        'coupon': '',
        'api_key': '<API_KEY>',
        'user_input': '{}'
    }
    ```
  - Headers: `{'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest'}`
  - Response thành công:
    ```json
    {
      "status": "success",
      "msg": "Tạo đơn hàng thành công!",
      "trans_id": "821P6a8977522f650",
      "data": [
        "mail1@hotmail.com|pass1|refresh_token1|client_id1",
        "mail2@hotmail.com|pass2|refresh_token2|client_id2"
      ]
    }
    ```
  - Dữ liệu trả về lưu trực tiếp vào `D:\Taadaa\Hotmail\hotmail_input.txt`.

---

## 2. Bẫy Lệch Cột / Ghi Nhầm Ngày vào `taikhoan_run_safe.xlsx` (Device ID)

- **Hiện tượng:** Khi chạy batch login hoặc preflight, gặp lỗi:
  `MACHINE_SERIAL_MISMATCH: machine=X resolved_serials=2 source=...taikhoan_run_safe.xlsx`
- **Nguyên nhân:** Các đợt reg TikTok trước ghi tracking bị lệch cột, ghi chuỗi ngày tháng (vd `21/08/2026` hoặc `2026-08-18 18:27:39`) vào cột 2 (`Device ID`) thay vì serial thật. Khi hàm `resolve_machine_serial_from_source` đọc cột 2 thấy 2 giá trị khác nhau cho cùng 1 máy sẽ ném exception fail-closed.
- **Cách khắc phục:**
  - Backup file: `taikhoan_run_safe.xlsx.bak-<timestamp>`
  - Đối chiếu danh sách serial chuẩn từ `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (cột 1: Máy, cột 2: Device ID).
  - Quét các ô cột 2 trong `taikhoan_run_safe.xlsx` chứa `/` hoặc `-` và ghi đè lại serial chuẩn từ file proxy.

---

## 3. Khóa Máy (DeviceLock) Tuần Tự & Guard Xoay Màn Hình (Portrait Guard)

- **DeviceLock per machine:**
  - Sử dụng `automation_core.device_lock.DeviceLock` bọc từng máy trong batch:
    ```python
    lock = DeviceLock(
        machine=int(machine),
        serial=serial,
        project="hotmail-login",
        user_authorized=True,
        bypass_proxy_readiness=True,
    )
    with lock:
        # Thao tác nạp tài khoản
    ```
- **Portrait Guard trước khi mở Outlook:**
  - Trên các máy Samsung S7 (Android 7/8), lệnh `wm user-rotation lock 0` có thể bị lỗi `Error: unknown command 'user-rotation'`.
  - Cách set xoay dọc triệt để an toàn:
    ```bash
    settings put system accelerometer_rotation 0
    settings put system user_rotation 0
    content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
    content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
    am force-stop com.microsoft.office.outlook
    ```
- **Xử lý màn hình "Chọn loại tài khoản" trên máy đã có tài khoản:**
  - Khi máy đã có sẵn 1 tài khoản, sau khi nhập email và ấn TIẾP TỤC, Outlook có thể hiển thị `ChooseAccountActivity` ("Chọn loại tài khoản").
  - Phải tap entry `btn_add_account_outlook` tại tâm bounds `(540, 576)` qua ATX JSON-RPC (`click`).
  - Sau khi vào Inbox, tài khoản mới sẽ xuất hiện ở thanh điều hướng bên trái (`account_navigation_view`) của Drawer.
