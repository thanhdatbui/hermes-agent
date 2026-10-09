# Dynamic Free Pool Auto-Updater & Dual-Layer Proxy Binding (OmniRoute & Hermes)

## 1. Bối cảnh & Bản chất của Model Free
- Các model miễn phí trên các hub công cộng (OpenRouter, OpenCode, public endpoints) có vòng đời ngắn, thường xuyên thay đổi trạng thái, bị giới hạn hoặc đột ngột chặn request qua proxy bên ngoài (ví dụ OpenCode chặn bằng `HTTP 403: OpenCode's free tier can only be used from within OpenCode` hoặc `HTTP 401: Model not supported`).
- Người dùng có thể có các ràng buộc loại trừ cứng (ví dụ: tuyệt đối không gắn Gemini 3.8 vào pool free để tránh đụng độ với luồng worker chính hoặc tránh ngốn quota phụ).
- Giải pháp bền vững: Xây dựng cơ chế Dynamic Discovery định kỳ từ OpenRouter Catalog (`https://openrouter.ai/api/v1/models`), sàng lọc model $0đ$, kiểm tra liveness thực tế, xếp hạng theo độ trễ và cập nhật combo tự động qua Cronjob.

---

## 2. Kỹ thuật Health-Check Liveness không gây nghẽn (Pitfalls & Solutions)
- **Cạm bẫy sập tải OpenRouter (Rate Limit / Concurrency Trap):**
  - OpenRouter Free Tier giới hạn nghiêm ngặt số lượng concurrent request (thường 1-2 request đồng thời).
  - Nếu dùng `ThreadPoolExecutor(max_workers=8)` hoặc nã đồng loạt toàn bộ catalog OpenRouter sẽ dẫn đến upstream trả về 429 hoặc timeout hàng loạt $\rightarrow$ toàn bộ model free bị kết luận DEAD giả tạo, script fallback rỗng hoặc timeout!
- **Quy trình Health-Check chuẩn:**
  1. Lọc thô từ catalog: `pricing.prompt == 0 and pricing.completion == 0`.
  2. Loại bỏ các model vi phạm guardrail:
     - Chặn model cấm: `gemini-3.8`, `3.8-flash`.
     - Chặn model phi ngôn ngữ/kiểm duyệt: `content-safety`, `moderation`.
  3. Kiểm tra song song với số luồng thấp: `max_workers = 2` (hoặc tối đa 4), timeout từng model 6–8s.
  4. Gom top model LIVE theo latency tăng dần (lấy 6-8 model nhanh nhất).
  5. Luôn kẹp 2 tầng chốt chặn fallback miễn phí từ ChatGPT Web (`chatgpt-web/gpt-5.6-luna-free` và `chatgpt-web/gpt-5.6-sol-instant`) vào cuối combo.
  6. Bước verify sau khi PATCH combo cần set timeout $\ge 25s$ vì fallback ChatGPT Web có latency ~10-15s.

---

## 3. Gắn Proxy Pool 2 Lớp (Dual-Layer Proxy Binding) cho Model Free
- **Tại sao cần:**
  - Nếu tất cả request model free đổ về OpenRouter từ một IP cố định, OpenRouter sẽ nhanh chóng rate-limit dải IP đó hoặc trả về lỗi 429/403.
- **Kiến trúc Proxy Pool 2 Lớp trên OmniRoute:**
  1. **Lớp Combo-level (`scope='combo'`):** Gán toàn bộ dải proxy vào combo `omni-free` (id: `5a72c9bc-94d8-4e35-a9c6-51545cb73d7a`).
  2. **Lớp Provider-level (`scope='provider'`):** Bật `proxy_enabled = 1` và gán dải proxy vào provider `openrouter`.
- **API cấu hình Proxy Pool trên OmniRoute (`:20129`):**
  - **Thiết lập chiến lược xoay vòng (`round-robin`):**
    ```http
    PATCH /api/settings/proxies/pool
    Content-Type: application/json

    {"scope": "provider", "scopeId": "openrouter", "strategy": "round-robin"}
    ```
    ```http
    PATCH /api/settings/proxies/pool
    Content-Type: application/json

    {"scope": "combo", "scopeId": "5a72c9bc-94d8-4e35-a9c6-51545cb73d7a", "strategy": "round-robin"}
    ```
  - **Gán từng proxy từ registry vào pool:**
    ```http
    PUT /api/settings/proxies/pool
    Content-Type: application/json

    {"scope": "provider", "scopeId": "openrouter", "proxyId": "<proxy_id>"}
    ```
    *(Tự động tạo bản ghi trong bảng `proxy_assignments` với `position` tăng dần, bảo toàn tính tuần tự khi xoay vòng)*.

---

## 4. Tự động hóa qua Watchdog Cronjob
- Script thực thi: `C:/Users/Kibe/AppData/Local/hermes/scripts/cron_omni_free_pool_updater.py`.
- Đăng ký Cronjob Hermes:
  - `action = 'create'`
  - `no_agent = True` (chạy script thuần túy không tốn token LLM)
  - `schedule = '0 */12 * * *'` (chạy lúc 00:00 và 12:00)
  - `deliver = 'telegram:-5373649734'` (báo cáo về nhóm Farm Alert)
- Luôn chạy `cron_sync_watchdog.py` sau khi tạo/sửa cronjob để đồng bộ `jobs.json` và script sang Git deploy và OneDrive Taadaa Sync an toàn.
