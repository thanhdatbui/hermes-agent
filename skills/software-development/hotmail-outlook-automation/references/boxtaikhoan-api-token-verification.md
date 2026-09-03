# BoxTaiKhoan API & Hotmail Token Verification

## 1. Mua Hotmail Tự Động Qua BoxTaiKhoan API
- **Endpoint**: `POST https://boxtaikhoan.com/ajaxs/client/product.php`
- **Headers**:
  - `Content-Type: application/x-www-form-urlencoded`
  - `X-Requested-With: XMLHttpRequest`
  - `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...`
- **Payload**:
  ```python
  data = {
      'action': 'buyProduct',
      'id': '60',  # Product 60: Hotmail Trust OAuth2 GraphAPI 393đ
      'variant_id': '0',
      'amount': 'N',
      'coupon': '',
      'api_key': API_KEY,
      'user_input': '{}'
  }
  ```
- **Response Format**: `json.loads(res)['data']` trả về danh sách chuỗi:
  `email|pass|refresh_token|client_id` (Client ID mặc định của Microsoft app: `9e5f94bc-e8a4-4e73-b8be-63364c29d753`).

## 2. Token Integrity & Graph API Verification Guard
- **MSA Artifacts Token Length**: Chuỗi `refresh_token` chuẩn của Microsoft dài từ **450 đến 525 ký tự** (bắt đầu bằng `M.C5...`).
- **Anti-Pattern (CloneFBIG 3470)**: Trên một số shop (như CloneFBIG gói 3470), trường CSDL lưu trữ bị giới hạn độ dài ký tự dẫn đến token bị cắt cụt còn 101 ký tự, gây lỗi `AADSTS70000: The provided value for the input parameter 'refresh_token' or 'assertion' is not valid`.
- **Quy trình Verification bắt buộc**: Trước khi ghi bất kỳ tài khoản Hotmail mới mua nào vào `gmail_clean_v2.xlsx`, BẮT BUỘC gọi `exchange_refresh_token(token, client_id)` để xác nhận đổi được Access Token (độ dài ~1400+ ký tự) từ máy chủ Microsoft (`https://login.microsoftonline.com/consumers/oauth2/v2.0/token`).

## 3. Quy chuẩn Chuẩn hóa `gmail_clean_v2.xlsx`
- **Xóa Placeholder rác**: Dọn dẹp các dòng có số máy nhưng trống cả `email` và `pass`.
- **Ép kiểu & Định dạng**:
  - Cột 1 (`số máy`): 100% kiểu số nguyên `int`, căn giữa (`center`).
  - Cột 2, 3, 4, 5, 9, 10 (`email, pass, 2fa, mail kp, token, client_id`): căn trái (`left`), font Calibri 11pt.
  - Cột 6, 7, 8, 11 (`ngày sinh, ngày tạo, mã phục hồi, trạng thái`): căn giữa (`center`).
- **Sắp xếp**: Sắp xếp tăng dần theo `số máy` (máy 1 -> 80), không để dồn tài khoản mới xuống đáy bảng.
