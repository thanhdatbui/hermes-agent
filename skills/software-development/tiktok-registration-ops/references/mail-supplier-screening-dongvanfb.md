# Kinh Nghiệm Sàng Lọc & Mua Hotmail/Outlook Reg TikTok Farm

## 1. Quy Ước Mô Tả Của Các Sàn Bán Mail MMO
- **Pitfall nhận diện:** Các sàn bán mail (như `dongvanfb.net`, các site đại lý MMO) thường **KHÔNG** ghi cụm từ *"Chưa qua TikTok"* hay *"Zin TikTok"*. Thay vào đó:
  - Chỉ khi hàng **ĐÃ QUA TIKTOK** thì họ mới chủ động gắn nhãn (VD: `Hotmail đã qua TikTok`, `Mail reg TikTok`, `Hàng qua Reg TikTok`).
  - Hàng thông thường mang tên kỹ thuật (VD: `Hotmail TRUSTED [GRAPH API]`, `Outlook TRUSTED`, `Hotmail PVA kèm mail khôi phục`) mà không kèm chữ "đã qua" thường là hàng nguồn gốc via/clone Facebook hoặc pool tạo tự động chưa phân loại.
- **Quy tắc điều phối:** Khi kiểm tra kho sàn không thấy chữ "Chưa qua TikTok", **CẤM** vội vàng khẳng định sàn không có hàng hay không dùng được. Cần:
  1. Phân tích rõ nhãn sàn (sàn có dán nhãn "đã qua TikTok" không, có dán nhãn "chưa qua dịch vụ" không).
  2. Báo cáo rõ tồn kho từng mã hàng có Graph API / OAuth2 token.
  3. Đề xuất mua test sample nhỏ (1–5 mail) để thực nghiệm trên 1 máy trước khi mua số lượng lớn.

## 2. Thông Số Kỹ Thuật Sàn dongvanfb.net
- **API Endpoint kiểm tra sản phẩm:** `GET https://api.dongvanfb.net/api/products_lists`
- **Các sản phẩm Hotmail/Outlook có Token (OAuth2 / Graph API):**
  - ID 5: `Hotmail TRUSTED [GRAPH API]` (350đ) - Chuyên Graph API.
  - ID 59: `Hotmail TRUSTED [IMAP/POP3/GRAPH API]` (350đ) - Hỗ trợ cả IMAP & Graph API.
  - ID 6: `Outlook TRUSTED [GRAPH API]` (350đ).
  - ID 57 / 58: `HOTMAIL / OUTLOOK TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM` (350đ) - Định dạng `email|pass|token|id|mail khôi phục`.
- **Cơ chế đọc OTP Graph API của sàn:**
  - Endpoint: `POST https://tools.dongvanfb.net/api/graph_messages`
  - Payload: `{"email": "<EMAIL>", "refresh_token": "<REFRESH_TOKEN>", "client_id": "<CLIENT_ID>"}`
  - Trả về danh sách messages kèm mã code OTP.

## 3. Quy Trình Hỗ Trợ User Đăng Nhập & Mua Test Nhanh
- Mở tab đăng nhập trên Chrome CDP cổng 9222:
  ```bash
  curl -s -X PUT "http://localhost:9222/json/new?https://dongvanfb.net/login"
  # Hoặc kích hoạt target:
  curl -s -X PUT "http://localhost:9222/json/activate/<target_id>"
  ```
- Hoặc mở trình duyệt mặc định trên Windows:
  ```bash
  cmd.exe /c start https://dongvanfb.net/login
  ```
