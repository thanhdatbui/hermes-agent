# BoxTaiKhoan API & Token Lifecycle Verification Lessons (2026-08-26)

## 1. Mua hàng qua BoxTaiKhoan API (Product ID: 60 - Hotmail OAuth2 Graph API)
- **Endpoint**: `POST https://boxtaikhoan.com/ajaxs/client/product.php`
- **Payload**: `action=buyProduct&id=60&amount=1&api_key=<API_KEY>`
- **Cơ chế nhận diện**: Mua theo vòng lặp `amount=1` để shop trả về trực tiếp mảng JSON `data: ["mail|pass|refresh_token|client_id"]`. Tránh mua bulk `amount > 1` trong một request vì shop chỉ trả về mã đơn hàng `trans_id`, đòi hỏi phải crawl qua giao diện web `/product-orders/` dễ bị chặn bởi Cloudflare/DOM session.

## 2. Quy tắc thẩm định Token sống (Verification Gate)
- **Độ dài token chuẩn**: Chuỗi `refresh_token` Graph API của Microsoft MSA Artifacts có độ dài chuẩn **450–525 ký tự** (thông dụng là **457 ký tự**).
- **Tuyệt đối cấm**:
  - Không copy chuỗi token rút gọn/rác (độ dài ~300 ký tự có mẫu lặp).
  - Không quy kết lỗi do shop bán khi chưa kiểm tra kỹ chuỗi token gốc nhận từ response API.
- **Quy trình kiểm tra sống (Live Exchange Test)**:
  - Gọi trực tiếp hàm `exchange_refresh_token(refresh_token, client_id)` lên endpoint `https://login.microsoftonline.com/consumers/oauth2/v2.0/token`.
  - Chỉ khi trả về `access_token` hợp lệ (không lỗi `AADSTS70000`) thì mới cho phép nạp tài khoản vào `gmail_clean_v2.xlsx`.

## 3. Quy trình Cách ly (Quarantine Protocol)
- Mọi tài khoản Hotmail bị lỗi token hoặc die thật sự:
  - BẮT BUỘC xóa khỏi kho sống `gmail_clean_v2.xlsx`.
  - Ghi vào file cách ly: `D:\Taadaa\Hotmail\hotmail_failed_quarantine.txt`.
  - Định dạng dòng cách ly: `email|pass|refresh_token|client_id|reason|timestamp`.
