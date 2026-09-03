# CloneFBIG / ShopClone7 Hotmail OAuth2 Extraction & Graph API Verification (2026-08-28)

## 1. Vấn Đề Cắt Cụt Token Qua API
- **Hiện tượng**: Khi gọi endpoint JSON API `POST /api/buy_product` trên CloneFBIG (sản phẩm `ID 3470` - Hotmail Graph API), mảng `data` trả về chuỗi tài khoản có refresh token bị cắt cụt (độ dài chỉ ~101 ký tự thay vì ~457–500 ký tự chuẩn MSA Artifacts).
- **Hậu quả**: Khi gửi token này lên máy chủ Microsoft (`https://login.microsoftonline.com/common/oauth2/v2.0/token`), Microsoft trả về lỗi:
  `AADSTS70000: The provided value for the input parameter 'refresh_token' or 'assertion' is not valid.`
- **Nguyên nhân**: Trường dữ liệu trong bảng CSDL hoặc bộ parser JSON API của shop bị giới hạn độ dài chuỗi trả về.

## 2. Giải Pháp Trích Xuất Token Chuẩn 100% Qua Web UI / CDP
1. **Mua đơn hàng**: Có thể gọi mua qua in-page AJAX trên Chrome CDP hoặc mua trực tiếp trên web.
2. **Lấy dữ liệu nguyên vẹn**:
   - Điều hướng tới trang chi tiết đơn hàng: `https://clonefbig.com/product-order/<trans_id>`
   - Trong bảng chi tiết, chuỗi đầy đủ được lưu tại thuộc tính `data-checkbox` của thẻ `<input type="checkbox" class="checkbox_product_sold">` hoặc tại `inputs[1]`:
     ```javascript
     let rows = Array.from(document.querySelectorAll('table tbody tr'));
     let accounts = rows.map(r => {
         let input = r.querySelector('input.checkbox_product_sold');
         return input?.getAttribute('data-checkbox') || '';
     }).filter(Boolean);
     ```
   - Định dạng chuẩn: `email|password|refresh_token|client_id|recovery_email`.

## 3. Xác Thực Live Trước Khi Nạp Kho
- **Quy trình bắt buộc**:
  1. Parse chuỗi `email`, `password`, `refresh_token`, `client_id` (mặc định client ID Thunderbird: `9e5f94bc-e8a4-4e73-b8be-63364c29d753`).
  2. Gọi hàm `exchange_refresh_token(refresh_token, client_id)` từ `hotmail_provider.py`.
  3. Chỉ khi nhận được `access_token` hợp lệ (độ dài ~1,504 bytes, `err=None`) mới ghi vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
  4. Luôn tạo backup file `gmail_clean_v2_backup_<timestamp>.xlsx` trước khi ghi dòng mới.
