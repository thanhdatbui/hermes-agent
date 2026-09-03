# BoxTaiKhoan.com API Purchase & OAuth2 Token Specs (2026-08-22)

## 1. BoxTaiKhoan.com API Endpoints

Hệ thống `boxtaikhoan.com` hỗ trợ các endpoint API tương thích tự động hóa qua `api_key`:

### a. Kiểm tra thông tin tài khoản & Số dư (Profile / Balance)
* **Endpoint:** `GET https://boxtaikhoan.com/api/profile.php?api_key=<API_KEY>`
* **Response:**
  ```json
  {
      "status": "success",
      "msg": "Lấy dữ liệu thành công!",
      "data": {
          "username": "thanhdatbui1995",
          "money": "270837"
      }
  }
  ```

### b. Lấy danh mục sản phẩm & Tồn kho (Products / Catalog)
* **Endpoint:** `GET https://boxtaikhoan.com/api/products.php?api_key=<API_KEY>`
* **Response:** Danh sách categories chứa products và variants, bao gồm `id`, `name`, `price`, `amount` (tồn kho).
* **ID sản phẩm Hotmail tiêu biểu:**
  * `ID 60`: Tài Khoản Hotmail Trust - OAuth2 [IMAP/POP3/GRAPH] Live 12-36 Months (393đ) — format `mail|pass|refresh_token|client_id`.
  * `ID 129`: Tài Khoản Hotmail TRUSTED GraphAPI - Live Vĩnh Viễn, Mail KP Fviainboxes (262đ) — format `mail|pass`.
  * `ID 59`: Tài Khoản Outlook Trusted OAuth2 (393đ) — format `mail|pass|refresh_token|client_id`.

### c. Mua hàng tự động (Buy Product Endpoint)
* **Endpoint:** `POST https://boxtaikhoan.com/ajaxs/client/product.php`
* **Headers:**
  * `Content-Type: application/x-www-form-urlencoded`
  * `X-Requested-With: XMLHttpRequest`
  * `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)`
* **Body Form Data:**
  ```
  action: buyProduct
  id: 60
  variant_id: 0
  amount: 1
  coupon: 
  api_key: <API_KEY>
  user_input: {}
  ```
* **Response Success:**
  ```json
  {
      "status": "success",
      "msg": "Tạo đơn hàng thành công!",
      "trans_id": "HF7Y6a89752508aa4",
      "data": [
          "email@hotmail.com|password|M.C528_BAY...|9e5f94bc-e8a4-4e73-b8be-63364c29d753"
      ]
  }
  ```

---

## 2. Microsoft OAuth2 Token Exchange & Mail API Specs

### a. Đổi Access Token từ Refresh Token:
* **Endpoint:** `POST https://login.microsoftonline.com/consumers/oauth2/v2.0/token`
* **Form Data:**
  ```
  client_id: 9e5f94bc-e8a4-4e73-b8be-63364c29d753
  grant_type: refresh_token
  refresh_token: <REFRESH_TOKEN>
  ```
* **Scope trả về từ token shop:**
  `https://outlook.office.com/Mail.ReadWrite https://outlook.office.com/EAS.AccessAsUser.All https://outlook.office.com/EWS.AccessAsUser.All https://outlook.office.com/POP.AccessAsUser.All https://outlook.office.com/IMAP.AccessAsUser.All https://outlook.office.com/SMTP.Send https://outlook.office.com/Mail.Send`

### b. Đọc tin nhắn / OTP:
* ⚠️ **Lưu ý quan trọng về Endpoint:** Vì scope được cấp gắn với `outlook.office.com`, gọi qua `https://graph.microsoft.com/v1.0/me/messages` sẽ bị `401 Unauthorized`.
* **Endpoint đúng:** `https://outlook.office.com/api/v2.0/me/messages?$top=3` (hoặc `/Mail.Read` qua Graph API nếu token có scope Graph).
* **Header:** `Authorization: Bearer <ACCESS_TOKEN>`

---

## 3. Quy trình nạp tự động vào Farm

1. **Lưu dữ liệu mua:** Thêm dòng mua được vào file nguồn `D:\Taadaa\Hotmail\hotmail_input.txt`.
2. **Chạy Runner nạp:**
   ```bash
   cd /d/Taadaa/Hotmail && env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe scripts/hotmail_list_runner.py --list hotmail_input.txt --machine-override <MÁY>
   ```
3. Sau khi login thành công trên thiết bị, runner tự động đồng bộ vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` và xóa dòng đã nạp khỏi `hotmail_input.txt`.
