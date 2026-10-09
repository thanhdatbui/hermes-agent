# Quản lý Pool Model Free & Gắn Proxy Luân Phiên (Dynamic Free Pool & Proxy Mesh)

## 1. Vấn đề cốt lõi của các Model Free
1. **Vòng đời ngắn & Tỷ lệ Die cao**:
   - Các model Free trên OpenRouter, OpenCode... thường xuyên thay đổi: bị gỡ bỏ, bị giới hạn rate limit ngặt nghèo hoặc bị chặn hoàn toàn.
   - *Ví dụ OpenCode*: Chặn toàn bộ request từ reverse proxy bên ngoài với lỗi:
     `HTTP 403: OpenCode's free tier can only be used from within OpenCode` & `HTTP 401: Model not supported`.
2. **Ràng buộc nghiệp vụ (Hard Invariants)**:
   - Khi thiết lập combo `omni-free` thuần túy, tuyệt đối KHÔNG gắn các model trả phí hoặc model bị cấm (`gemini-3.8`, `3.8-flash`) vào combo.
   - Loại bỏ các model lọc nội dung (`content-safety`, `moderation`).

---

## 2. Kiến trúc Auto-Updater cho Combo Free (`cron_omni_free_pool_updater.py`)

### Quy trình tự động hóa (Mỗi 12 tiếng):
1. **Lấy danh mục trực tiếp từ OpenRouter Catalog**:
   - Endpoint: `https://openrouter.ai/api/v1/models`
   - Điều kiện lọc: `float(pricing.prompt) == 0 and float(pricing.completion) == 0`
   - Loại trừ: `gemini-3.8`, `3.8-flash`, `content-safety`, `moderation`.

2. **Kỷ luật kiểm tra sức khỏe (Health Check Pitfalls)**:
   - **CẢNH BÁO RATE LIMIT OPENROUTER**: OpenRouter Free Tier chỉ cho phép 1-2 request đồng thời. Nếu dùng `ThreadPoolExecutor` với `max_workers >= 8`, request sẽ bị dội hàng loạt hoặc timeout, dẫn đến nhận định sai là toàn bộ model bị chết.
   - **Giải pháp**:
     - Ưu tiên danh sách model chất lượng cao đã biết (`KNOWN_PRIORITY_MODELS` như `nex-n2.5-pro:free`, `laguna-xs-2.1:free`, `qwen3.8-27b:free`, `ling-3.0-flash:free`, `lfm-2.5-2.6b:free`).
     - Giới hạn concurrency `max_workers = 2`, timeout mỗi ping 4-7s.
     - Dừng quét sớm (Early Exit) ngay khi gom đủ 4-6 model sống khỏe để hoàn thành tác vụ trong < 15 giây.

3. **Chốt chặn Fallback vững chắc**:
   - Luôn ghép 2 tầng cuối cùng từ cụm ChatGPT Web Free:
     - `chatgpt-web/gpt-5.6-luna-free`
     - `chatgpt-web/gpt-5.6-sol-instant`
   - Đặt timeout xác minh combo sau khi patch lên 25-30s để vượt qua độ trễ của web session.

4. **Cập nhật Live qua REST API**:
   - Gọi `PATCH http://127.0.0.1:20129/api/combos/<omni-free-id>`
   - Cấu hình chuẩn:
     ```json
     {
       "strategy": "priority",
       "config": {
         "maxRetries": 1,
         "retryDelayMs": 100,
         "targetTimeoutMs": 25000,
         "queueTimeoutMs": 1000,
         "stickyRoundRobinLimit": 1,
         "disableSessionStickiness": true,
         "maxGlobalAttempts": 8,
         "nestedComboMode": "execute",
         "failoverBeforeRetry": true
       }
     }
     ```

---

## 3. Gắn Proxy Pool Luân Phiên (Double-Layer Proxy Mesh)

Khi gọi model Free qua OpenRouter, nếu đi bằng IP thật hoặc 1 IP duy nhất sẽ rất nhanh chóng bị rate-limit hoặc chặn dải. Cần gắn dàn Proxy Farm luân phiên theo 2 lớp:

### Lớp 1: Cấp Provider (`scope: provider, scopeId: openrouter`)
- Bật `proxy_enabled = 1` trong bảng `provider_connections` cho connection OpenRouter (`d8e441bf-...`).
- Đặt chiến lược xoay vòng: `strategy: round-robin`.
- Đẩy toàn bộ danh sách proxy ID từ `proxy_registry` (hoặc proxy pool Antigravity) vào `proxy_assignments` với `scope='provider'`, `scope_id='openrouter'`.

### Lớp 2: Cấp Combo (`scope: combo, scopeId: <combo-id>`)
- Gán toàn bộ danh sách proxy vào combo `omni-free` qua API:
  `PUT /api/settings/proxies/pool`
  ```json
  {
    "scope": "combo",
    "scopeId": "5a72c9bc-94d8-4e35-a9c6-51545cb73d7a",
    "proxyId": "<proxy-uuid>"
  }
  ```
- Đặt strategy cho combo:
  `PATCH /api/settings/proxies/pool`
  ```json
  {
    "scope": "combo",
    "scopeId": "5a72c9bc-94d8-4e35-a9c6-51545cb73d7a",
    "strategy": "round-robin"
  }
  ```

### Kiểm chứng thực tế:
- Kiểm tra log `proxy_logs` trong `storage.sqlite` để xác nhận request đi qua các IP proxy khác nhau (`mirotik1.taadaa.click:10005`, `10006`, `10025`...) thay vì direct connection.
