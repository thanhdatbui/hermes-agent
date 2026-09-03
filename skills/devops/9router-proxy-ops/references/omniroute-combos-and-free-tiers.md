# OmniRoute Combos & Free Tiers Guide

## 1. Runtime DB & Ports
- **9Router**: `:20128` — DB: `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`
- **OmniRoute**: `:20129` — Active DB: `C:\Users\Kibe\.omniroute\storage.sqlite` (Note: do not confuse with `AppData\Roaming\omniroute\storage.sqlite`).

## 2. Hard Rules & Operational Invariants
- **CẤM TỰ Ý GÁN / THAY ĐỔI PROXY / DB DATA**: Tuyệt đối không tự ý chạy `INSERT/UPDATE` gán proxy vào database cho các account chưa được chỉ định nhằm mục đích "đồng bộ". Báo cáo trung thực hiện trạng (account nào có proxy thì báo, account nào chạy Direct/Pool thì báo đúng vậy).
- **CẤM GHI LUNG TUNG VÀO GLOBAL MEMORY**: Các quy tắc vận hành proxy, tools và hạ tầng thuộc về project docs/skills, không được ghi vào global memory làm nặng token context.
- **Rule for Creating / Updating Combos & Connections**: Always create/update combos via the live HTTP API `POST /api/combos`, `PUT /api/combos/[id]`, or `DELETE /api/combos/[id]` rather than raw SQLite inserts. Raw DB inserts bypass in-memory route caches (`getCombosCachedForChat()`), causing `400 Unable to determine provider for model`.

### Connection Configuration API Notes:
- **Concurrency**: Set `maxConcurrent` via `PATCH /api/providers/[id]` with `{"maxConcurrent": 8}` (cho tài khoản Pro) hoặc `{"maxConcurrent": 3}` (cho tài khoản Free / Starter Quota). Nâng lên 8 giúp 12 tài khoản Pro đạt dung lượng ~96 request đồng thời.
- **Semaphore Timeout**: File `open-sse/services/accountSemaphore.ts` dùng `DEFAULT_TIMEOUT_MS` (mặc định 90.000ms qua biến `ACCOUNT_SEMAPHORE_TIMEOUT_MS`). Tránh để 30s vì các request context lớn (100k–180k tokens) mất 6–10s/lượt khiến hàng đợi dễ văng `SEMAPHORE_TIMEOUT`.
- **Rate Limit Protection**: Toggle `rateLimitProtection` via `POST /api/rate-limits` with `{"connectionId": "<id>", "enabled": true}` (the `/api/providers/[id]` route intentionally rejects direct mutation of `rateLimitProtection` to prevent silent drift with the rate limiter engine).
- **Google Antigravity Starter Quota (Free) vs Pro in Pool**:
  - **Pro accounts**: `maxConcurrent: 8`, `rateLimitProtection: true`, xếp ở các slot ưu tiên đầu (`pool-1` .. `pool-N`).
  - **Free / Starter Quota accounts**: `maxConcurrent: 3` (tránh nghéz RPM/burst), `rateLimitProtection: true` (bắt buộc để cooldown tự động bỏ qua khi hết quota), xếp ở **cuối danh sách targets** của combo `ag-gemini-pool-3` (ví dụ `pool-13 (starter-quota)`) làm tầng dự phòng sâu (Deep Standby).

### Combo Routing & Cooldown Invariants:
- **Persisted Cooldown Skip**: Hàm `resolvePersistedConnectionCooldownSkipReason` kiểm tra mốc `rateLimitUntil`. Các tài khoản đang cooldown được bỏ qua tức thì (0ms), không gửi request thử.
- **Spillover & Full-Pool Exhaustion**: Request ưu tiên nạp vào `pool-1`; khi chạm `maxConcurrent=8` sẽ tự động tràn (spillover) sang `pool-2` .. `pool-13`. Nếu toàn bộ 13 account đều kín slot/hết quota/timeout, OmniRoute trả 429 và Telegram Gateway hiển thị `The model provider is rate-limiting requests`.
- **Payload Optimization (Chống nghẽn Semaphore)**: Khi review/audit, CHỈ gửi `git diff -U5` + rubric + danh sách test case. CẤM đọc nguyên văn toàn bộ file test/mock XML hàng chục nghìn dòng nhét vào prompt (đẩy context lên 180k tokens làm nghẽn toàn bộ pool). Context gọn (~10k-20k tokens) giúp Gemini phản hồi trong 10-15s và nhả slot ngay lập tức.

## 3. Free Tiers vs Paid Models Distinction
- **100% Free / No-Auth**:
  - `opencode` (`oc/nemotron-3.5-lightning-free`, `oc/nemotron-3-ultra-free`, `oc/mimo-v2.5-free`, `oc/laguna-s-2.1-free`, `oc/hy3-free`, `oc/big-pickle`).
  - `openrouter` `:free` models (`nvidia/nemotron-3-ultra-550b-a55b:free`, `z-ai/glm-5.2:free`, `google/gemma-4-31b-it:free`, `cohere/north-mini-code:free`).
  - Rate limits are IP-based or free-tier per-minute caps.
- **Google Antigravity (Preview / OAuth Pool)**:
  - Uses standard Gmail accounts without paid Google One / Plus / Pro subscription.
  - Generates `claude-opus-4-6-thinking`, `claude-sonnet-4-6`, `gemini-3.7-flash-high`.
- **Paid Models (Codex / ChatGPT Plus/Pro)**:
  - `GPT-5.5`, `GPT-5.6-sol/terra/luna` require paid ChatGPT Plus/Pro accounts. Never confuse these with free-tier combos.

## 4. Canonical Combo Architectures in OmniRoute

### A. Pure Free OpenCode Combo (`omni-free`)
- **Purpose**: 100% free open models without consuming Antigravity/Google quota or mobile proxy bandwidth.
- **Priority Fallback Chain (Strongest & Most Stable -> Lightweight Final Fallback)**:
  1. `oc/nemotron-3.5-lightning-free` (NVIDIA Nemotron 3.5 Lightning - Fast Open Reasoning)
  2. `oc/laguna-s-2.1-free` (Poolside Laguna S 2.1 - Fast Coding & General)
  3. `oc/muse-spark-1.2-contributor-free` (Muse Spark 1.2 - Fast Lightweight Chat ~2.7s)
  4. `oc/nemotron-3-ultra-free` (NVIDIA Nemotron 3 Ultra - Heavy Reasoning Fallback)
  5. `oc/mimo-v2.5-free` (Xiaomi MiMo 2.5 - General Chat Fallback)
  6. `oc/big-pickle` (Big Pickle - Super-fast ~1.2s Final Fail-safe Safety Net)

```bash
curl -X POST http://localhost:20129/api/combos \
  -H "Content-Type: application/json" \
  -d '{
    "name": "omni-free",
    "strategy": "priority",
    "models": [
      {"model": "oc/nemotron-3.5-lightning-free", "provider": "opencode", "label": "Nemotron 3.5 Lightning"},
      {"model": "oc/laguna-s-2.1-free", "provider": "opencode", "label": "Poolside Laguna S 2.1"},
      {"model": "oc/muse-spark-1.2-contributor-free", "provider": "opencode", "label": "Muse Spark 1.2"},
      {"model": "oc/nemotron-3-ultra-free", "provider": "opencode", "label": "Nemotron 3 Ultra"},
      {"model": "oc/mimo-v2.5-free", "provider": "opencode", "label": "Xiaomi MiMo 2.5"},
      {"model": "oc/big-pickle", "provider": "opencode", "label": "Big Pickle"}
    ],
    "config": {
      "maxRetries": 0,
      "retryDelayMs": 0,
      "handoffThreshold": 0.85,
      "handoffModel": "",
      "maxMessagesForSummary": 30,
      "trackMetrics": true,
      "reasoningTokenBufferEnabled": true,
      "failoverBeforeRetry": true,
      "zeroLatencyOptimizationsEnabled": false,
      "resetAwareQuotaCacheTtlMs": 0,
      "resetAwareQuotaCacheMaxStaleMs": 0
    },
    "description": "Combo thuần model OpenCode Free (không chứa AG)"
  }'
```

### B. Dedicated Antigravity Combos (`ag-claude` & `ag-opus`)
- **`ag-claude`**: `antigravity/claude-sonnet-4-6` -> fallback `ag-gemini-pool-3` (pool 10 account Google Gemini 3.7 Flash).
- **`ag-opus`**: `antigravity/claude-opus-4-6-thinking` -> fallback `ag-gemini-pool-3`.
- **`ag-gemini-pool-3`**: Dedicated pool of 10 Antigravity Google accounts with high context and Ordered Priority Spillover (nominal capacity: 50 requests). Target models must pin `connectionId` and `label: pool-1` ... `pool-10`.

## 5. Proxy Attachment & Fallback Architecture (Rules & Resolution Hierarchy)

### Resolution Hierarchy in OmniRoute (`src/lib/db/proxies/rotation.ts`)
1. **Normal Flow (Sticky Pinned Proxy):**
   - Khi request gọi đến account, OmniRoute kiểm tra `proxy_assignments` ở cấp `scope = 'account'`.
   - Nếu account có gán proxy (ví dụ `dokieu` ➔ `mobi11`), request đi đúng qua proxy đó.
2. **Proxy Failure / Dead Fallback:**
   - Nếu proxy gán riêng cho account bị chết / rớt mạng, hàm `resolveScopePoolInternal` không tìm thấy alive proxy ở `scope = 'account'` và **tự động fallback xuống `scope = 'provider'`**.
   - Tại scope provider (`antigravity`), hệ thống bốc một proxy sống trong pool (69 mobi proxies) để thực hiện request.
3. **Account Error / Quota Fallback:**
   - Nếu lỗi xuất phát từ phía account (429 Rate Limit, 403 Validation, hết quota), combo engine (`priority`) tự động failover sang account kế tiếp trong danh sách combo.

## 6. Exposing OmniRoute Combos on Hermes (`config.yaml`)
To make custom combos visible in Telegram `/model` selector:
Under `providers.omni.models`:
```yaml
providers:
  omni:
    api: http://127.0.0.1:20129/v1
    key_env: OMNIROUTE_API_KEY
    transport: chat_completions
    default_model: ag-gemini-pool-3
    models:
      ag-gemini-pool-3: {}
      omni-free: {}
      ag-claude: {}
      ag-opus: {}
```
