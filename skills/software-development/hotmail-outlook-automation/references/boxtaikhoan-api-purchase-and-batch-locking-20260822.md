# BoxTaiKhoan API Purchase & Batch Hotmail Login with DeviceLock — 2026-08-22

## 1. BoxTaiKhoan.com API Purchase Automation

Web shop `boxtaikhoan.com` hỗ trợ mua tự động qua API Key mà không bị chặn Cloudflare hay Captcha:

- **Check Balance & Profile:**
  - `GET https://boxtaikhoan.com/api/profile.php?api_key=<API_KEY>`
  - Response: `{"status":"success","data":{"username":"...","money":"270837"}}`
- **Get Products Catalog & Stock:**
  - `GET https://boxtaikhoan.com/api/products.php?api_key=<API_KEY>`
  - Returns category tree, product IDs, variant IDs, price, and stock amounts.
  - Hotmail Loại 2 (OAuth2 Token): Product ID `60` (393đ/acc, stock ~55k+).
  - Hotmail Loại 1 (TRUSTED GraphAPI - MailKP): Product ID `129` (262đ/acc, stock ~26k+).
- **Mua tài khoản (Purchase Endpoint):**
  - `POST https://boxtaikhoan.com/ajaxs/client/product.php`
  - Headers: `User-Agent: Mozilla/5.0`, `Content-Type: application/x-www-form-urlencoded`, `X-Requested-With: XMLHttpRequest`
  - Body params (URL-encoded):
    ```python
    {
        "action": "buyProduct",
        "id": "60",          # Product ID
        "variant_id": "0",
        "amount": "26",      # Quantity
        "coupon": "",
        "api_key": "<API_KEY>",
        "user_input": "{}"
    }
    ```
  - Response:
    ```json
    {
      "status": "success",
      "msg": "Tạo đơn hàng thành công!",
      "trans_id": "821P6a8977522f650",
      "data": [
        "ahanneythonn@hotmail.com|chrisd1087|M.C528_BAY...|9e5f94bc-e8a4-4e73-b8be-63364c29d753",
        "..."
      ]
    }
    ```
- **Lưu trữ:** Lưu trực tiếp `data` vào `D:\Taadaa\Hotmail\hotmail_input.txt`.

---

## 2. Quy tắc Batch Login Hotmail & Khóa Thiết Bị (DeviceLock)

- **DeviceLock per machine:**
  ```python
  from automation_core.device_lock import DeviceLock

  lock = DeviceLock(
      machine=int(machine),
      serial=serial,
      project="hotmail-login",
      user_authorized=True,
      bypass_proxy_readiness=True
  )
  with lock:
      # Thực hiện login Outlook app trên máy
      ...
  ```
  - Tự động tạo lock file tại `C:\Users\Kibe\.codex\device-locks\machine_<m>.lock.json` và `serial_<s>.lock.json` trong lúc thao tác.
  - Tự động nhả khóa ngay khi hoàn tất thành công.

- **Bảo vệ hiển thị xoay dọc (Portrait Lock):**
  - Tránh lỗi màn hình ngang làm `OUTLOOK_APP_LOGIN_FORM_NOT_IDENTIFIED` (do nút Continue `btn_primary_button` bị thay đổi thành `menu_continue` trên ActionBar ngang).
  - Trước khi mở app Outlook, bắt buộc set portrait & force-stop:
    ```python
    subprocess.run([adb, "-s", serial, "shell", "settings", "put", "system", "accelerometer_rotation", "0"])
    subprocess.run([adb, "-s", serial, "shell", "settings", "put", "system", "user_rotation", "0"])
    subprocess.run([adb, "-s", serial, "shell", "content", "insert", "--uri", "content://settings/system", "--bind", "name:s:accelerometer_rotation", "--bind", "value:i:0"])
    subprocess.run([adb, "-s", serial, "shell", "content", "insert", "--uri", "content://settings/system", "--bind", "name:s:user_rotation", "--bind", "value:i:0"])
    subprocess.run([adb, "-s", serial, "shell", "am", "force-stop", "com.microsoft.office.outlook"])
    ```

- **Lỗi `MACHINE_SERIAL_MISMATCH` do Ngày tháng lẫn vào cột Device ID:**
  - Trong `taikhoan_run_safe.xlsx` sheet `Accounts`, nếu cột `Device ID` (col 2) bị gán nhầm chuỗi ngày tháng (vd `21/08/2026`) $\rightarrow$ `resolve_machine_serial_from_source` sẽ phát hiện $\ge 2$ serial khác nhau và ném lỗi `MACHINE_SERIAL_MISMATCH`.
  - Phải audit và đối chiếu với `PROXYgandienthoai.xlsx` để khôi phục đúng serial cho máy trước khi chạy runner.
