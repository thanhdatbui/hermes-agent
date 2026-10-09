# Codex OAuth Phone Verification, 5sim Automation & Reseller APIs

## 1. Bản chất phân định ChatGPT Web vs Codex CLI trong OmniRoute (:20129)

| Thuộc tính | ChatGPT Web (`chatgpt-web-pool`) | Codex CLI (`codex`) |
| :--- | :--- | :--- |
| **Giao thức** | Web Session (`chatgpt.com/backend-api/conversation`) | Official REST API (`api.openai.com` qua OAuth PKCE) |
| **Trần Payload** | Bị WAF Cloudflare chặn cứng **~500KB - 1MB** -> Nổ **HTTP 413 Payload Too Large** khi agent prompt / tool schemas phình to | Nhận payload lớn nhiều MB, full context 128k - 200k tokens |
| **Thứ tự trong Combo**| **BẮT BUỘC ĐỂ DƯỚI** các provider nuốt context lớn (Antigravity Gemini, Claude, Codex). Tránh để ChatGPT Web ở Tier 2 hứng tràn từ Agent vì sẽ cascade 413 hàng loạt | Ưu tiên cao hoặc ngang hàng các pool chính |
| **Điều kiện kích hoạt** | Chỉ cần Google SSO login trên trình duyệt | Bắt buộc qua cổng `https://auth.openai.com/add-phone` xác minh OTP SMS |

---

## 2. Quy trình & Kinh nghiệm thực tế tích hợp 5sim API cho OpenAI

### API Endpoints chuẩn (Header: `Authorization: Bearer <TOKEN>`):
- **Bảng giá & Tỷ lệ realtime:** `GET https://5sim.net/v1/guest/prices?product=openai`
  - Luôn quét động trước mỗi mẻ, lọc theo `cost <= max_price` và sort theo `rate72 / rate168`.
- **Mua số:** `GET https://5sim.net/v1/user/buy/activation/{country}/{operator}/openai`
- **Check OTP:** `GET https://5sim.net/v1/user/check/{order_id}`
- **Hủy số hoàn tiền:** `GET https://5sim.net/v1/user/cancel/{order_id}`
- **Hoàn tất:** `GET https://5sim.net/v1/user/finish/{order_id}`

### Bẫy thực tế & Bài học xương máu:
1. **Ảo tưởng số siêu rẻ ($\le \$0.10$):**
   - Các nước Anh (+44, $0.06), Argentina (+54, $0.05), Brazil (+55, $0.07), Nam Phi (+27, $0.10) bị OpenAI áp dụng **Silent Drop** (OpenAI báo đã gửi nhưng gateway chặn không đẩy SMS sang nhà mạng).
   - Tỷ lệ thực tế dải này gần như 0%. Dù 5sim hoàn tiền 100% khi cancel nhưng làm hao phí hàng chục phút chờ đợi.
2. **Thời gian chờ SMS (Polling Timeout):**
   - Không nên đặt < 60s. Thời gian tối ưu là **120s (2 phút)** để đón các SMS quốc tế bị delay định tuyến.
3. **Phân khúc nhận code thực tế:**
   - **USA (`virtual63` - ~$0.148):** Rate thực tế **>60%**.
   - **Hy Lạp (`virtual34` - ~$0.149):** Rate thực tế **>45%**.

---

## 3. Khai thác API Đấu Kho Hàng Reseller (Ví dụ: `sumistore.me`)

Nhiều shop tài khoản MMO sử dụng chuẩn REST API Tele-Shop để chia sẻ kho hàng đại lý:
- **Base URL:** `https://<domain>` (vd: `https://sumistore.me`)
- **Header xác thực:** `X-Tele-API-ID: <API_ID>` (Lấy từ bot Telegram của shop mục API, format `TAPI-...`, KHÔNG PHẢI Telegram User ID số nguyên).
- **Endpoint tra cứu:**
  - `GET /api/tele-products`: Liệt kê sản phẩm, stock, giá bán.
  - `GET /api/tele-balance`: Tra cứu số dư ví bot.
- **Endpoint mua hàng:**
  - `POST /api/tele-product/buy`
  - Body: `{"id": "<product_key>", "quantity": 1}`
  - Bảo mật HMAC: `HMAC-SHA256(secret=API_ID, message="timestamp|nonce|body")`
  - Header: `X-Timestamp`, `X-Nonce`, `X-Signature`, `X-Idempotency-Key`, `Prefer: respond-async`.

### Bài toán kinh tế Mua Acc Ver Sẵn vs Thuê SIM:
- Khi shop có bán mặt hàng **`CHAT GPT FREE ĐÃ VER PHONE CODEX`** với giá **~4.000đ** (sẵn hàng):
  - Chi phí 4.000đ tương đương giá thuê 1 SMS Mỹ trên 5sim (~3.700đ), nhưng **tiết kiệm 100% thời gian automation, tránh rủi ro miss code hoặc delay OTP**.
  - Ưu tiên mua thẳng acc ver sẵn qua API nạp vào pool OmniRoute thay vì tự code giải OTP thủ công.
