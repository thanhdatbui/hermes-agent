# Fviainboxes.com Recovery Email OTP Endpoint & Extraction

## 1. Bản chất dịch vụ
- `fviainboxes.com` là dịch vụ web Temp Mail công khai chạy SPA (Vue 3 / Vite), không phải server nội bộ đóng kín.
- Rất nhiều tài khoản Hotmail/Outlook mua từ các shop MMO (BoxTaiKhoan, DongVanFB, v.v.) sử dụng email khôi phục có domain `@fviainboxes.com` (ví dụ: `murtaghshandy1563pf@fviainboxes.com`).
- Cấm kết luận vội vàng rằng domain này không lấy được thư/OTP.

## 2. API Endpoints đọc hộp thư
Website cung cấp REST API trực tiếp tại cùng domain:

- **Danh sách thư của hòm mail:**
  ```http
  GET https://fviainboxes.com/messages?username={username}&domain=fviainboxes.com
  ```
  *Ví dụ:* với email `murtaghshandy1563pf@fviainboxes.com`:
  ```bash
  curl -s "https://fviainboxes.com/messages?username=murtaghshandy1563pf&domain=fviainboxes.com"
  ```
  Phản hồi JSON:
  ```json
  {"result": [{"id": 12345, "from": "account-security-noreply@accountprotection.microsoft.com", "subject": "Microsoft account security code", "createdAt": "..."}]}
  ```

- **Chi tiết thư / Nội dung lấy mã OTP:**
  ```http
  GET https://fviainboxes.com/message?username={username}&domain=fviainboxes.com&id={id}
  ```
  Phản hồi JSON chứa trường `data` (HTML/Text body) và trích xuất regex 6-7 chữ số OTP Microsoft gửi về.

## 3. Web UI fallback qua CDP / Browser
Nếu gọi curl bị chặn bởi Cloudflare Turnstile hoặc WAF:
1. Mở trang `https://fviainboxes.com/` trực tiếp trên profile browser đang chạy (GPM profile của acc).
2. Điền username vào `#username`, chọn domain `fviainboxes.com` (mặc định).
3. Bấm submit button (`Get Email`).
4. Đọc danh sách thư hiển thị ngay trong DOM hoặc evaluate `fetch('/messages?username=...&domain=fviainboxes.com')` trong context của tab đó.
