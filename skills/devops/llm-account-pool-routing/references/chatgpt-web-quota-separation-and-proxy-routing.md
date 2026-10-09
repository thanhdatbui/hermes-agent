# ChatGPT-Web vs Codex Quota Separation & Per-Account Proxy Routing

Tài liệu đúc kết thực chiến về phân định cơ chế quota độc lập của OpenAI và quy trình gán proxy di động 1-1 cho các connection trên OmniRoute (:20129).

## 1. Sự Thật Về Quota: Codex Developer Pool vs ChatGPT-Web
- **Hiện tượng:** Cùng một tài khoản Gmail, khi gọi qua provider `codex` (`gpt-5.5` hoặc `gpt-5.6-terra-high`) bị lỗi `503 Unavailable (reset after 700h)` (~29–30 ngày), nhưng khi gọi qua provider `chatgpt-web` (`gpt-5.6-luna-free`, `gpt-5.6-sol-high`) thì trả về `200 OK` phà phà.
- **Bản chất:** OpenAI phân tách rạch ròi 2 hệ thống hạn ngạch:
  1. **Codex CLI / Developer Pool**: Áp dụng giới hạn token/lượt gọi theo tháng cho developer tool. Khi chỉ có 1-2 tài khoản gánh combo `review`, hạn ngạch sẽ cạn sạch trong vòng vài tiếng và bị khóa cứng cả tháng.
  2. **ChatGPT Web Pool**: Áp dụng hạn ngạch theo phiên sử dụng web thông thường hàng ngày/hàng giờ, không liên thông với developer pool.
- **Khả năng gọi chéo Model:** Trên OmniRoute, provider `chatgpt-web` vẫn gọi được trơn tru dòng model code reasoning cao cấp như **`gpt-5.6-sol-high`**, **`gpt-5.6-sol-xhigh`** và **`gpt-5.6-terra-high`**, giúp combo `review` hoạt động bền bỉ mà không lo cạn quota.

## 2. Các Cạm Bẫy SSO & Onboarding Khi Lấy Token Web
1. **Bẫy Năm Sinh 2026 trên Form DateField Tiếng Việt:**
   - OpenAI tự động khởi tạo giá trị ngày tháng năm sinh bằng ngày hiện tại của máy (`14/09/2026`).
   - Nếu script không dùng `Control+A` xóa sạch số `2026`, form sẽ gửi năm sinh 2026 (tuổi = 0) -> OpenAI chặn báo đỏ và văng lỗi `token_exchange_failed`.
   - Bắt buộc bôi đen xóa và nhập năm sinh trong khoảng `1996` – `2002` (24–30 tuổi).
2. **Bẫy Ô Input Tuổi Trực Tiếp `input[name="age"]`:**
   - Ở một số giao diện tiếng Anh/Việt khác, form chỉ có 1 ô `age`. Nếu script chỉ tìm DateField thì ô tuổi bị bỏ trống -> timeout 60s -> OpenAI văng ngược về màn hình *"Phiên của bạn đã kết thúc"*.
3. **Màn Hình "Phiên của bạn đã kết thúc" (`auth.openai.com/u/login`):**
   - Chỉ là màn hình chuyển tiếp trung gian khi phiên trước bị timeout. Nhận diện nút đen to **[Đăng nhập]** và click tự động là trình duyệt quay lại luồng Google SSO.
4. **Phân Biệt Auth Token vs Cookie Guest:**
   - Chỉ lưu token khi chuỗi bắt đầu bằng **`eyJhbG...`** (Base64 JWT header) và kiểm tra giao diện `chatgpt.com` có 0 nút "Đăng nhập".

## 3. Quy Trình Gán Proxy Di Động 1-1 trên OmniRoute
Để tránh lộ IP máy chủ và chống rate-limit chéo giữa các tài khoản:
1. Trích xuất cổng proxy từ profile GPM (ví dụ `5113` trong `test.taadaa.click:5113`).
2. Tra cứu `GET /api/settings/proxies` trên OmniRoute để tìm `proxy_id` của port đó.
3. Gán Proxy Assignment bằng phương thức `PUT`:
   ```python
   requests.put("http://127.0.0.1:20129/api/settings/proxies/assignments", json={
       "proxyId": proxy_id,
       "scope": "account",
       "scopeId": connection_id
   })
   # Kích hoạt cờ proxyEnabled trên connection
   requests.put(f"http://127.0.0.1:20129/api/providers/{connection_id}", json={
       "proxyEnabled": True
   })
   ```
4. Xác minh: Gửi request completion tới connection đó với timeout 60s, đảm bảo traffic được định tuyến chính xác qua cổng proxy di động tương ứng.
