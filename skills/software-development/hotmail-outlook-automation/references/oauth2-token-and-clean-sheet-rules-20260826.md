# Microsoft Graph OAuth2 Refresh Token & BoxTaiKhoan Sourcing Standards (2026-08-26)

## 1. Quy cách Chuỗi Token Microsoft Graph API
- Chuỗi `refresh_token` chuẩn của Microsoft Graph API mua từ shop (BoxTaiKhoan product 60) luôn có độ dài khoảng **457 ký tự**.
- **Bắt buộc kiểm chứng Live**: Trước khi nạp tài khoản vào kho dữ liệu (`gmail_clean_v2.xlsx`), phải chạy hàm `exchange_refresh_token(tok, cid)` gửi trực tiếp lên Microsoft OAuth2 endpoint `https://login.microsoftonline.com/consumers/oauth2/v2.0/token`.
- Tuyệt đối không lưu các token bị cắt cụt (ví dụ ~309 ký tự) gây lỗi `AADSTS70000 (status 400)`.

## 2. Chiến lược Mua & Trích xuất từ BoxTaiKhoan
- **Mua tự động qua API**: Sử dụng `POST /ajaxs/client/product.php` với `amount=1` qua vòng lặp. Việc mua lẻ từng đơn giúp nhận trực tiếp mảng JSON `data` chứa đầy đủ `mail|pass|refresh_token|client_id`.
- **Khôi phục đơn cũ qua Chrome Kal CDP**:
  - Khởi động Chrome profile `Kal` (`Profile 4`) với cờ `--remote-debugging-port=9222`.
  - Kết nối CDP và điều hướng tới `/client/product-orders?limit=100`.
  - Mở chi tiết từng đơn hàng `/product-order/<trans_id>` và đọc text từ `textarea.account-field` hoặc `input.checkbox_product_sold[data-checkbox]`.

## 3. Quy tắc Sắp xếp Kho `gmail_clean_v2.xlsx`
- **CẤM NHÉT DỒN HÀNG XUỐNG ĐÁY BẢNG**: Toàn bộ dữ liệu trong `gmail_clean_v2.xlsx` bắt buộc được sắp xếp tăng dần theo `Số Máy` (từ Máy 1 -> Máy 80).
- Khi gán tài khoản Hotmail mới cho máy nào, phải chèn đúng vào nhóm hàng của máy đó.

## 4. Cơ chế Đọc OTP / Magic Link Fail-Closed
- Toàn bộ Hotmail Loại 2 (đã có `refresh_token`) **100% đọc mã OTP và Magic Link URL từ xa trên PC qua Graph API**.
- **TUYỆT ĐỐI CẤM** tự ý bật app Outlook trên điện thoại khi tài khoản đã có token Graph API.
