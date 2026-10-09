# ChatGPT-Web Pool GPM 5-Worker Healer & Session-Token Invariants

## 1. User Directives & Concurrency Mandate (2026-09-30)

- **Concurrency**: Khi chạy batch hồi sinh tài khoản ChatGPT-Web qua GPMLogin v3, **BẮT BUỘC dùng 5 workers song song (`ThreadPoolExecutor(max_workers=5)`)**, TUYỆT ĐỐI CẤM chạy tuần tự 1-by-1 vì quá chậm. Máy host Kibe (32–64GB RAM) dư sức gánh 5 tiến trình GPM Chromium đồng thời.
- **Ranh giới tài nguyên**: Tiến trình GPMLogin chạy trên Windows desktop, **hoàn toàn độc lập với thiết bị Android Phone Farm**. Không được viện cớ "sợ nghẽn farm" hay "sợ tràn RAM" để tự ý bóp xuống 1 worker.
- **Lịch chạy**: Giữ nguyên lịch **05:00 AM sáng hàng ngày** (`0 5 * * *`) cho cronjob `chatgpt-web-pool-healer-watchdog` (`cron_chatgpt_web_pool_watchdog.py`), đảm bảo dàn acc Web được hồi sinh đầy đủ trước ca làm việc ban ngày.

---

## 2. Token Extraction & Schema Invariants (Fix lỗi HTTP 401 trên OmniRoute)

### A. Lỗi kinh điển của các script watchdog cũ:
- Script cũ lấy toàn bộ cookies qua Playwright `context.cookies(["https://chatgpt.com"])` rồi gộp dạng:
  `k1=v1; k2=v2; __Secure-next-auth.session-token=eyJ...; ...`
- OmniRoute (`open-sse/executors/chatgpt-web.ts`) kỳ vọng `apiKey` là **chính chuỗi JWT `session-token`** (bắt đầu bằng `eyJhbG...`), không phải chuỗi cookie thô HTTP header.
- Nạp chuỗi cookie thô khiến OmniRoute trả về lỗi:
  `[401]: ChatGPT auth failed — re-paste your __Secure-next-auth.session-token cookie from chatgpt.com.`

### B. Hàm trích xuất chuẩn xác (hỗ trợ ghép chunk `.0`, `.1`):
```python
def extract_clean_session_token(context):
    cookies = context.cookies(["https://chatgpt.com"])
    s_tok = None
    chunks = {}
    for c in cookies:
        cn, cv = c.get("name", ""), c.get("value", "")
        if cn == "__Secure-next-auth.session-token":
            s_tok = cv
            break
        elif cn.startswith("__Secure-next-auth.session-token."):
            chunks[cn.split(".")[-1]] = cv
    if not s_tok and chunks:
        sorted_keys = sorted(chunks.keys(), key=lambda x: int(x) if x.isdigit() else x)
        s_tok = "".join(chunks[k] for k in sorted_keys)
    return s_tok
```

---

## 3. Automation Flow Vượt Checkpoint & Onboarding OpenAI

Khi mở profile GPM qua Proxy Mobi 4G, IP di động sạch sẽ tự động vượt qua Cloudflare Turnstile / Sentinel mà không bị chặn bot. Tuy nhiên Playwright CDP phải tự động giải quyết 3 tình huống kẹt giao diện:

1. **Màn hình "Phiên của bạn đã kết thúc" / "Your session has ended":**
   - Click nút `[Đăng nhập]` / `[Log in]`.
   - Click `Continue with Google` (`button[data-provider="google"]`).
2. **Màn hình Google Account Chooser & Consent:**
   - Click đúng tài khoản Google theo email: `div[data-identifier*="<email>"]`.
   - Trang Consent Google (`/oauth/id`): Bắt buộc click nút `[Tiếp tục]` / `[Continue]`.
3. **Form OpenAI Onboarding (`about-you`):**
   - Nếu OpenAI bắt xác nhận thông tin cá nhân:
     - Điền tên: `input[name="name"] = email.split('@')[0].capitalize()`
     - **Điền tuổi (Age) - BẮT BUỘC**: `input[name="age"] = "24"`
     - Click `button[type="submit"]` / `[Tiếp tục]`.
   - *Cảnh báo*: Nếu bỏ quên ô `age`, trang web sẽ báo lỗi *"Nhập độ tuổi hợp lệ để tiếp tục"*, treo 60s và OpenAI sẽ hủy phiên làm văng về màn hình đăng nhập.

---

## 4. Cập nhật Database OmniRoute & Test Inference Sau Khi Hồi Sinh

Sau khi có `session-token` hợp lệ, thực thi atomic update vào SQLite (`~/.omniroute/storage.sqlite`):
```sql
UPDATE provider_connections 
SET api_key = ?, 
    is_active = 1, 
    test_status = 'active', 
    last_error = NULL, 
    last_error_at = NULL, 
    backoff_level = 0, 
    rate_limited_until = NULL, 
    updated_at = CURRENT_TIMESTAMP 
WHERE id = ?;
```
Bắt buộc có bước kiểm chứng **Inference Gate**: Bắn 1 request nhỏ vào model `chatgpt-web/gpt-5.6-sol-high` qua cổng `:20129` để xác nhận HTTP 200 trước khi báo cáo thành công.
