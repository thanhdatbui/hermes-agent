# Cấu hình Codex Pool Cache-Optimized & Wire Model Aliases vào Hermes

## 1. Khác biệt cốt lõi: P2C vs Cache-Optimized cho LLM Pool
- **Chiến lược `p2c` (Power of Two Choices):**
  - Ưu điểm: Cân bằng tải cực tốt khi lưu lượng lớn, né tài khoản nghẽn/lỗi.
  - Nhược điểm: Phân tán các turn kế tiếp nhau trong cùng một session qua nhiều tài khoản khác nhau, dẫn tới **mất hoàn toàn Prompt Caching** (mỗi turn phải đọc và tính lại toàn bộ system prompt và context lịch sử, gây trễ và tốn quota token).
- **Chiến lược `cache-optimized` (Chuẩn áp dụng giống `ag-gemini-pool-3`):**
  - **Session Stickiness:** `disableSessionStickiness: false` — Ghim toàn bộ các turn của cùng một session vào một account cố định.
  - **Prompt Cache Affinity:** `disablePromptCacheAffinity: false` — Ưu tiên phân phối các request có chung system prompt/prefix vào tài khoản đã lưu cache.
  - **Sticky Round-Robin Limit:** `8` — Số turn ghim session trước khi cân nhắc phân phối lại.
  - **Max Global Attempts:** Bằng tổng số accounts trong pool (ví dụ `7`) để khi account hiện tại gặp lỗi/rate-limit, OmniRoute tự động failover qua các account còn lại mà không ngắt quãng turn.
  - **Target Timeout:** `90.000ms`, `retryDelayMs: 200`, `maxRetries: 1`, `nestedComboMode: "execute"`, `failoverBeforeRetry: true`.

## 2. Ma trận hỗ trợ Model của OpenAI Codex CLI Pool
- **Hỗ trợ mượt mà (HTTP 200 OK):**
  - `codex/gpt-5.6-terra` (Model coding chuyên sâu)
  - `codex/gpt-5.6-luna` (Model chat/coding tốc độ cao)
- **Bị OpenAI từ chối (HTTP 400 Bad Request):**
  - `codex/gpt-5.6-sol`: OpenAI trả về `{"error":{"message":"[400]: {\"detail\":\"The 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account.\"}"}}`.
  - Muốn dùng Sol bắt buộc phải gọi qua session cookie web của pool `chatgpt-web-pool`, không gọi qua provider `codex`.

## 3. Quy trình tạo Combo trên OmniRoute (:20129)
Endpoint tạo combo: `POST http://127.0.0.1:20129/api/combos` hoặc cập nhật `PATCH http://127.0.0.1:20129/api/combos/<id>`:
```json
{
  "name": "omni-luna",
  "description": "OmniRoute Codex Luna Pool (7 accounts, cache-optimized)",
  "strategy": "cache-optimized",
  "models": [
    {
      "id": "omni-luna-model-1",
      "kind": "model",
      "model": "codex/gpt-5.6-luna",
      "providerId": "codex",
      "connectionId": "<connection_uuid>",
      "weight": 0,
      "label": "codex-1: ..."
    }
  ],
  "config": {
    "maxRetries": 1,
    "retryDelayMs": 200,
    "targetTimeoutMs": 90000,
    "stickyRoundRobinLimit": 8,
    "disableSessionStickiness": false,
    "disablePromptCacheAffinity": false,
    "maxGlobalAttempts": 7,
    "nestedComboMode": "execute",
    "failoverBeforeRetry": true
  }
}
```
*Lưu ý:* Khi tạo combo để Hermes gọi dạng bare model name (`omni-terra`, `omni-luna`), bắt buộc phải có combo mang đúng tên đó trên OmniRoute, nếu không OmniRoute sẽ trả về `400: Unable to determine provider for model 'omni-terra'`.

## 4. Quy trình Wire Model & Alias vào Hermes (`config.yaml`)
Không chỉnh sửa trực tiếp YAML tay để bảo vệ tính toàn vẹn indent và gateway. Sử dụng `hermes config set`:

1. **Cập nhật catalog model ở cả 2 nhánh (Legacy List + V12 Dict):**
   ```bash
   # Nhánh legacy custom_providers (tìm đúng index của provider omni, ví dụ index 1)
   hermes config set custom_providers.1.models.omni-terra.context_length 256000
   hermes config set custom_providers.1.models.omni-luna.context_length 256000

   # Nhánh providers.omni (v12+ schema)
   hermes config set providers.omni.models.omni-terra.context_length 256000
   hermes config set providers.omni.models.omni-luna.context_length 256000
   ```

2. **Tạo Model Aliases cho phép switch nhanh:**
   ```bash
   hermes config set model.aliases.omni-terra custom:omni/omni-terra
   hermes config set model.aliases.omni-luna custom:omni/omni-luna
   ```

3. **Kiểm tra và nghiệm thu:**
   - Trong Hermes CLI hoặc Telegram gateway: gõ `/model omni-terra` hoặc `/model omni-luna`.
   - `hermes_cli.model_switch.resolve_alias` sẽ resolve thành `('custom:omni', 'omni-terra', 'omni-terra')`.
   - Bắn ping thử request đến `http://127.0.0.1:20129/v1/chat/completions` xác nhận HTTP 200 và response model trả về khớp.
