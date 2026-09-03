# CloneFBIG Hotmail Token Truncation Pitfall & Exchange Verification

## Incident & Root Cause
- Khi mua tài khoản Hotmail/Outlook Graph API (ví dụ sản phẩm ID 3470 trên `clonefbig.com` qua API `/api/buy_product`), CSDL hoặc script export của bên cung cấp có thể bị giới hạn độ dài trường chuỗi, dẫn đến `refresh_token` bị cắt ngắn chỉ còn ~101 ký tự (chuỗi chuẩn Microsoft MSA Artifacts thường dài 450–525 ký tự).
- Khi script gọi Microsoft OAuth2 token endpoint (`https://login.microsoftonline.com/common/oauth2/v2.0/token`), Microsoft trả về lỗi:
  `AADSTS70000: The provided value for the input parameter 'refresh_token' or 'assertion' is not valid.`

## Quy tắc kiểm tra trước khi nạp / mua sỉ
1. **Kiểm tra độ dài chuỗi token:**
   - Token hợp lệ chuẩn MSA phải có độ dài tối thiểu > 400 ký tự.
   - Nếu `len(refresh_token) < 400`, lập tức gắn cờ nghi ngờ token bị cắt cụt.
2. **Kiểm tra live token exchange:**
   - Luôn mua thử nghiệm 1–2 tài khoản và gọi hàm `exchange_refresh_token(refresh_token, client_id)` trước khi đặt mua số lượng lớn.
   - Chỉ khi đổi thành công Access Token (thường dài ~1,400–1,500 ký tự) mới tiến hành nạp vào `gmail_clean_v2.xlsx`.
